import argparse
import hashlib
import os
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config


np.random.seed(Config.RANDOM_STATE)

COLUNAS_DATASET = [
    'paciente_id', 'nome', 'faixa_etaria', 'tipo_pagamento', 'faltas_anteriores',
    'taxa_historica', 'tempo_como_paciente', 'data', 'horario', 'dia_semana',
    'turno', 'procedimento', 'antecedencia_dias', 'e_retorno', 'n_remarcacoes',
    'proximo_feriado', 'condicao_clima', 'temperatura', 'compareceu'
]


def _faixa_etaria_from_idade(idade_raw):
    if pd.isna(idade_raw):
        return '36-60'

    if isinstance(idade_raw, (int, float)):
        idade = int(idade_raw)
    else:
        texto = str(idade_raw)
        match = re.search(r'(\d+)', texto)
        idade = int(match.group(1)) if match else 40

    if idade <= 17:
        return '0-17'
    if idade <= 35:
        return '18-35'
    if idade <= 60:
        return '36-60'
    return '60+'


def _mascarar_nome(nome):
    tokens = [t for t in str(nome).strip().split() if t]
    if not tokens:
        return 'Paciente'
    return ' '.join(f'{token[0].upper()}.' for token in tokens[:3])


def _gerar_id_lgpd(nome, idx):
    base = f'{str(nome).strip().lower()}::{idx}'
    digest = hashlib.sha256(base.encode('utf-8')).hexdigest()[:10].upper()
    return f'PACR{digest}'


def _resolver_coluna(df, candidatos):
    lower_map = {col.lower(): col for col in df.columns}
    for candidato in candidatos:
        if candidato in lower_map:
            return lower_map[candidato]
    for col in df.columns:
        normalizada = col.lower()
        if any(candidato in normalizada for candidato in candidatos):
            return col
    return None


def carregar_pacientes_reais(caminho_entrada):
    caminho = Path(caminho_entrada)
    if not caminho.exists():
        raise FileNotFoundError(f'Arquivo de pacientes não encontrado: {caminho}')

    print(f"[LOAD] Lendo base real de pacientes: {caminho}")
    if caminho.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(caminho)
    else:
        df = pd.read_csv(caminho)

    col_nome = _resolver_coluna(df, ['paciente', 'nome'])
    col_idade = _resolver_coluna(df, ['idade'])
    col_pagamento = _resolver_coluna(df, ['pagamento', 'convenio', 'convênio'])

    if not col_nome:
        raise ValueError('A planilha precisa ter uma coluna de paciente/nome.')

    base = df[[col_nome] + ([col_idade] if col_idade else []) + ([col_pagamento] if col_pagamento else [])].copy()
    base = base.rename(columns={col_nome: 'nome_raw'})

    if col_idade:
        base = base.rename(columns={col_idade: 'idade_raw'})
    else:
        base['idade_raw'] = np.nan

    if col_pagamento:
        base = base.rename(columns={col_pagamento: 'tipo_pagamento_raw'})
    else:
        base['tipo_pagamento_raw'] = 'Não informado'

    base['nome_raw'] = base['nome_raw'].astype(str).str.strip()
    base = base[base['nome_raw'].ne('') & base['nome_raw'].ne('nan')]
    base = base.drop_duplicates(subset=['nome_raw']).reset_index(drop=True)

    # LGPD: não carregar documento/celular/prontuário para dataset de ML.
    rng = np.random.default_rng(Config.RANDOM_STATE)
    pacientes = []
    for idx, row in base.iterrows():
        faixa = _faixa_etaria_from_idade(row['idade_raw'])
        pagamento_raw = str(row['tipo_pagamento_raw']).strip()
        pagamento = pagamento_raw if pagamento_raw and pagamento_raw.lower() != 'nan' else 'Não informado'
        if pagamento not in ['Particular', 'Convênio', 'SUS', 'Não informado']:
            pagamento = 'Não informado'

        faltas_anteriores = int(rng.poisson(0.7))
        taxa_historica = float(np.clip(rng.beta(2, 7), 0.01, 0.95))
        tempo_como_paciente = int(rng.integers(1, 73))

        pacientes.append({
            'paciente_id': _gerar_id_lgpd(row['nome_raw'], idx),
            'nome': _mascarar_nome(row['nome_raw']),
            'faixa_etaria': faixa,
            'tipo_pagamento': pagamento,
            'faltas_anteriores': faltas_anteriores,
            'taxa_historica': round(taxa_historica, 3),
            'tempo_como_paciente': tempo_como_paciente
        })

    pacientes_df = pd.DataFrame(pacientes)
    print(f"   [OK] {len(pacientes_df)} pacientes reais carregados (nome mascarado + ID pseudônimo)")
    return pacientes_df


def _gerar_registro_consulta(paciente, data_consulta, rng):
    dia_semana = data_consulta.strftime('%A')
    mes = data_consulta.month

    hora = int(rng.choice([8, 9, 10, 11, 14, 15, 16, 17, 18]))
    horario = f'{hora:02d}:00'
    turno = 'Manhã' if hora < 12 else ('Tarde' if hora < 18 else 'Noite')

    procedimento = rng.choice(['Consulta', 'Limpeza', 'Obturação', 'Extração', 'Canal', 'Clareamento'])
    antecedencia_dias = int(rng.choice([1, 2, 3, 5, 7, 10, 15, 21, 30]))
    e_retorno = int(rng.choice([0, 1], p=[0.7, 0.3]))
    n_remarcacoes = int(rng.choice([0, 1, 2, 3], p=[0.68, 0.22, 0.07, 0.03]))
    proximo_feriado = int(rng.choice([0, 1], p=[0.85, 0.15]))
    condicao_clima = rng.choice(['ensolarado', 'nublado', 'chuvoso', 'tempestade'], p=[0.45, 0.30, 0.20, 0.05])

    if mes in [12, 1, 2, 3]:
        temperatura = int(rng.integers(25, 38))
    elif mes in [6, 7, 8]:
        temperatura = int(rng.integers(15, 28))
    else:
        temperatura = int(rng.integers(20, 32))

    prob_base = 0.20
    if dia_semana == 'Monday':
        prob_base += 0.20
    elif dia_semana == 'Friday':
        prob_base += 0.10

    if paciente['tipo_pagamento'] == 'Particular':
        prob_base -= 0.10
    elif paciente['tipo_pagamento'] == 'SUS':
        prob_base += 0.12
    elif paciente['tipo_pagamento'] == 'Não informado':
        prob_base += 0.04

    if antecedencia_dias > 20:
        prob_base += 0.22
    elif antecedencia_dias > 15:
        prob_base += 0.15
    elif antecedencia_dias > 7:
        prob_base += 0.08

    if hora >= 17:
        prob_base += 0.14
    elif hora == 8:
        prob_base += 0.07

    prob_base += n_remarcacoes * 0.18

    if mes in [1, 7]:
        prob_base += 0.10
    elif mes == 12:
        prob_base += 0.07

    prob_base += paciente['faltas_anteriores'] * 0.12
    prob_base += paciente['taxa_historica'] * 0.30

    if procedimento in ['Canal', 'Extração']:
        prob_base -= 0.10
    elif procedimento == 'Consulta':
        prob_base += 0.08

    if proximo_feriado:
        prob_base += 0.12

    if paciente['tempo_como_paciente'] < 6:
        prob_base += 0.08
    if paciente['faixa_etaria'] == '18-35':
        prob_base += 0.06

    if condicao_clima == 'chuvoso':
        prob_base += 0.10
    elif condicao_clima == 'tempestade':
        prob_base += 0.18
    elif condicao_clima == 'ensolarado':
        prob_base -= 0.04

    if temperatura > 35 or temperatura < 18:
        prob_base += 0.06

    prob_falta = float(np.clip(prob_base, 0.01, 0.95))
    compareceu = 1 if rng.random() > prob_falta else 0

    return {
        'paciente_id': paciente['paciente_id'],
        'nome': paciente['nome'],
        'faixa_etaria': paciente['faixa_etaria'],
        'tipo_pagamento': paciente['tipo_pagamento'],
        'faltas_anteriores': paciente['faltas_anteriores'],
        'taxa_historica': paciente['taxa_historica'],
        'tempo_como_paciente': paciente['tempo_como_paciente'],
        'data': data_consulta.strftime('%Y-%m-%d'),
        'horario': horario,
        'dia_semana': dia_semana,
        'turno': turno,
        'procedimento': procedimento,
        'antecedencia_dias': antecedencia_dias,
        'e_retorno': e_retorno,
        'n_remarcacoes': n_remarcacoes,
        'proximo_feriado': proximo_feriado,
        'condicao_clima': condicao_clima,
        'temperatura': temperatura,
        'compareceu': compareceu
    }


def gerar_dados_de_pacientes_reais(pacientes_df):
    print(f"[GEN] Gerando histórico de consultas para {len(pacientes_df)} pacientes reais...")
    rng = np.random.default_rng(Config.RANDOM_STATE)
    dados = []
    data_inicio = datetime.now() - timedelta(days=365)

    for _, paciente in pacientes_df.iterrows():
        n_consultas = int(rng.integers(2, 6))
        for _ in range(n_consultas):
            dias_offset = int(rng.integers(0, 365))
            data_consulta = data_inicio + timedelta(days=dias_offset)
            dados.append(_gerar_registro_consulta(paciente, data_consulta, rng))

    df = pd.DataFrame(dados, columns=COLUNAS_DATASET)
    taxa_falta = (1 - df['compareceu'].mean()) * 100

    print(f"   [OK] Histórico criado: {len(df)} consultas")
    print(f"   [>] Taxa de falta: {taxa_falta:.1f}%")
    print(f"   [>] Pacientes únicos: {df['paciente_id'].nunique()}")
    return df


def gerar_dados_simulados(n_registros=1200):
    print(f"[GEN] Gerando {n_registros} registros simulados (fallback)...")
    rng = np.random.default_rng(Config.RANDOM_STATE)
    dados = []
    data_inicio = datetime.now() - timedelta(days=365)

    for i in range(n_registros):
        paciente = {
            'paciente_id': f'PACS{i + 1:05d}',
            'nome': f'P. {i + 1}',
            'faixa_etaria': rng.choice(['0-17', '18-35', '36-60', '60+']),
            'tipo_pagamento': rng.choice(['Particular', 'Convênio', 'SUS']),
            'faltas_anteriores': int(rng.poisson(0.6)),
            'taxa_historica': float(np.clip(rng.beta(2, 8), 0.01, 0.95)),
            'tempo_como_paciente': int(rng.integers(1, 60))
        }
        dias_offset = int(rng.integers(0, 365))
        data_consulta = data_inicio + timedelta(days=dias_offset)
        dados.append(_gerar_registro_consulta(paciente, data_consulta, rng))

    return pd.DataFrame(dados, columns=COLUNAS_DATASET)


def _encontrar_arquivo_real():
    if os.environ.get('REAL_PATIENTS_PATH'):
        return os.environ['REAL_PATIENTS_PATH']

    candidatos = [
        Path(BASE_DIR) / 'Listagem_pacientes-dra_larissa_d._teixeira_cro_15.528-2026-05-01.xlsx',
        Path(BASE_DIR) / 'dados' / 'pacientes.csv',
        Path(BASE_DIR) / 'dados' / 'pacientes.xlsx',
    ]
    for caminho in candidatos:
        if caminho.exists():
            return str(caminho)
    return None


def main():
    parser = argparse.ArgumentParser(description='Gerador de dataset para OdontoSync')
    parser.add_argument('--simulado', action='store_true', help='Força geração totalmente simulada')
    args = parser.parse_args()

    os.makedirs(Config.DADOS_DIR, exist_ok=True)

    arquivo_real = _encontrar_arquivo_real()
    if not args.simulado and arquivo_real:
        pacientes_df = carregar_pacientes_reais(arquivo_real)
        df = gerar_dados_de_pacientes_reais(pacientes_df)
        origem = f'real ({arquivo_real})'
    else:
        if not args.simulado:
            print('[WARN] Base real não encontrada. Usando fallback simulado.')
        df = gerar_dados_simulados(n_registros=1200)
        origem = 'simulado'

    df.to_csv(Config.CSV_PATH, index=False)
    print(f"\n[OK] Dataset salvo em: {Config.CSV_PATH}")
    print(f"   [>] Origem: {origem}")
    print(f"   [>] Total: {len(df)} registros")
    print(f"   [>] Colunas: {', '.join(df.columns)}")


# Diretório base do projeto (resolvido no final para uso em _encontrar_arquivo_real)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))


if __name__ == '__main__':
    main()
