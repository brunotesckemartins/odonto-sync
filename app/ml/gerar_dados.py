import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config

# Configurar seed para reprodutibilidade
np.random.seed(42)

def gerar_dados_simulados(n_registros=1200):
    """
    Gera dataset simulado com padrões clínicos realistas.
    
    Padrões embutidos:
    - Segunda-feira tem mais faltas
    - Convênio particular falta menos
    - Antecedência longa aumenta risco
    - Fim do dia aumenta risco
    - Remarcações aumentam risco
    - Sazonalidade: janeiro e julho têm mais faltas
    """
    
    print(f"[GEN] Gerando {n_registros} registros simulados...")
    
    dados = []
    
    # Período: últimos 12 meses
    data_inicio = datetime.now() - timedelta(days=365)
    
    for i in range(n_registros):
        # Data aleatória nos últimos 12 meses
        dias_offset = np.random.randint(0, 365)
        data_consulta = data_inicio + timedelta(days=dias_offset)
        
        # Extrair características temporais
        dia_semana = data_consulta.strftime('%A')  # Monday, Tuesday, etc
        mes = data_consulta.month
        
        # Horário da consulta
        hora = np.random.choice([8, 9, 10, 11, 14, 15, 16, 17, 18], 
                               p=[0.1, 0.15, 0.15, 0.1, 0.1, 0.15, 0.15, 0.05, 0.05])
        horario = f"{hora:02d}:00"
        
        # Turno
        if hora < 12:
            turno = "Manhã"
        elif hora < 18:
            turno = "Tarde"
        else:
            turno = "Noite"
        
        # Tipo de pagamento
        tipo_pagamento = np.random.choice(['Particular', 'Convênio', 'SUS'], 
                                         p=[0.3, 0.5, 0.2])
        
        # Faixa etária
        faixa_etaria = np.random.choice(['0-17', '18-35', '36-60', '60+'], 
                                       p=[0.15, 0.35, 0.35, 0.15])
        
        # Procedimento
        procedimento = np.random.choice([
            'Consulta', 'Limpeza', 'Obturação', 
            'Extração', 'Canal', 'Clareamento'
        ], p=[0.25, 0.25, 0.20, 0.10, 0.10, 0.10])
        
        # Características do paciente
        faltas_anteriores = np.random.poisson(0.5)  # Maioria tem 0-1 faltas
        tempo_como_paciente = np.random.randint(1, 60)  # meses
        taxa_historica = np.random.beta(2, 8)  # Maioria tem taxa baixa (0-0.3)
        
        # Características da consulta
        antecedencia_dias = np.random.choice([1, 2, 3, 5, 7, 10, 15, 21, 30], 
                                            p=[0.05, 0.1, 0.15, 0.2, 0.2, 0.15, 0.1, 0.03, 0.02])
        e_retorno = np.random.choice([0, 1], p=[0.7, 0.3])
        n_remarcacoes = np.random.choice([0, 1, 2, 3], p=[0.7, 0.2, 0.07, 0.03])
        
        # Próximo feriado (simplificado: se está a menos de 5 dias de um feriado)
        proximo_feriado = np.random.choice([0, 1], p=[0.85, 0.15])
        
        # ========== FEATURES CLIMÁTICAS (preparação para API futura) ==========
        # Condição climática: influencia faltas (dados sintéticos realistas)
        # Padrões: chuva aumenta faltas, sol diminui
        condicao_clima = np.random.choice(
            ['ensolarado', 'nublado', 'chuvoso', 'tempestade'], 
            p=[0.45, 0.30, 0.20, 0.05]
        )
        
        # Temperatura: valores realistas para clima brasileiro
        if mes in [12, 1, 2, 3]:  # Verão
            temperatura = np.random.randint(25, 38)
        elif mes in [6, 7, 8]:  # Inverno
            temperatura = np.random.randint(15, 28)
        else:  # Primavera/Outono
            temperatura = np.random.randint(20, 32)
        
        # ========== CÁLCULO DA PROBABILIDADE DE FALTA (PADRÕES REALISTAS) ==========
        prob_base = 0.20  # 20% de falta base
        
        # Padrão 1: Segunda-feira falta MUITO mais (+20%)
        if dia_semana == 'Monday':
            prob_base += 0.20
        elif dia_semana == 'Friday':
            prob_base += 0.10
        
        # Padrão 2: Particular falta MUITO menos (-15%), SUS falta mais (+12%)
        if tipo_pagamento == 'Particular':
            prob_base -= 0.15
        elif tipo_pagamento == 'SUS':
            prob_base += 0.12
        
        # Padrão 3: Antecedência longa aumenta MUITO o risco
        if antecedencia_dias > 20:
            prob_base += 0.25
        elif antecedencia_dias > 15:
            prob_base += 0.18
        elif antecedencia_dias > 7:
            prob_base += 0.10
        
        # Padrão 4: Fim do dia e horários ruins
        if hora >= 17:
            prob_base += 0.15
        elif hora == 8:  # Primeira consulta do dia
            prob_base += 0.08
        
        # Padrão 5: Remarcações aumentam MUITO o risco
        prob_base += n_remarcacoes * 0.20
        
        # Padrão 6: Sazonalidade mais forte (janeiro e julho)
        if mes in [1, 7]:
            prob_base += 0.12
        elif mes == 12:  # Dezembro também
            prob_base += 0.08
        
        # Padrão 7: Histórico de faltas é MUITO importante
        prob_base += faltas_anteriores * 0.15
        
        # Padrão 8: Taxa histórica do paciente é crítica
        prob_base += taxa_historica * 0.30
        
        # Padrão 9: Procedimentos mais complexos têm menos faltas
        if procedimento in ['Canal', 'Extração']:
            prob_base -= 0.12
        elif procedimento == 'Consulta':
            prob_base += 0.08  # Consulta simples falta mais
        
        # Padrão 10: Próximo a feriado aumenta muito o risco
        if proximo_feriado:
            prob_base += 0.15
        
        # Padrão 11: Pacientes novos faltam mais
        if tempo_como_paciente < 6:
            prob_base += 0.10
        
        # Padrão 12: Jovens faltam mais
        if faixa_etaria == '18-35':
            prob_base += 0.08
        
        # Padrão 13: CLIMA - Chuva aumenta faltas significativamente
        if condicao_clima == 'chuvoso':
            prob_base += 0.12
        elif condicao_clima == 'tempestade':
            prob_base += 0.20  # Tempestade aumenta muito mais
        elif condicao_clima == 'ensolarado':
            prob_base -= 0.05  # Tempo bom diminui levemente
        
        # Padrão 14: Temperaturas extremas aumentam faltas
        if temperatura > 35 or temperatura < 18:
            prob_base += 0.08
        
        # Garantir que a probabilidade está entre 0 e 1
        prob_falta = np.clip(prob_base, 0.01, 0.95)
        
        # Determinar se faltou (com um pouco de aleatoriedade)
        compareceu = 1 if np.random.random() > prob_falta else 0
        
        # Criar registro
        registro = {
            'paciente_id': f'PAC{i+1:04d}',
            'nome': f'Paciente {i+1}',
            'faixa_etaria': faixa_etaria,
            'tipo_pagamento': tipo_pagamento,
            'faltas_anteriores': faltas_anteriores,
            'taxa_historica': round(taxa_historica, 3),
            'tempo_como_paciente': tempo_como_paciente,
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
        
        dados.append(registro)
    
    # Criar DataFrame
    df = pd.DataFrame(dados)
    
    # Estatísticas
    taxa_falta = (1 - df['compareceu'].mean()) * 100
    print(f"\n[DATA] Estatísticas do dataset gerado:")
    print(f"  [>] Total de registros: {len(df)}")
    print(f"  [>] Taxa de falta: {taxa_falta:.1f}%")
    print(f"  [>] Compareceram: {df['compareceu'].sum()}")
    print(f"  [>] Faltaram: {(1 - df['compareceu']).sum()}")
    print(f"\n[STATS] Distribuição por tipo de pagamento:")
    print(df['tipo_pagamento'].value_counts())
    print(f"\n[STATS] Distribuição por dia da semana:")
    print(df['dia_semana'].value_counts())
    
    return df

def main():
    """Gera o dataset e salva em CSV"""
    
    # Garantir que o diretório existe
    os.makedirs(Config.DADOS_DIR, exist_ok=True)
    
    # Gerar dados
    df = gerar_dados_simulados(n_registros=1200)
    
    # Salvar CSV
    df.to_csv(Config.CSV_PATH, index=False)
    print(f"\nOK Dataset salvo em: {Config.CSV_PATH}")
    print(f"   Total: {len(df)} registros")
    
    # Mostrar primeiras linhas
    print(f"\n📄 Primeiras 5 linhas:")
    print(df.head())

if __name__ == '__main__':
    main()
