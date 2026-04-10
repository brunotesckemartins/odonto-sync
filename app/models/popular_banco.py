import pandas as pd
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config
from app.models.database import get_connection, init_db

def popular_banco():
    """Popula o banco de dados com os dados do CSV gerado"""
    
    print("📦 Populando banco de dados...")
    
    # Verificar se o CSV existe
    if not os.path.exists(Config.CSV_PATH):
        print(f"❌ Erro: CSV não encontrado em {Config.CSV_PATH}")
        print("   Execute primeiro: python -m app.ml.gerar_dados")
        return
    
    # Carregar dados do CSV
    df = pd.read_csv(Config.CSV_PATH)
    print(f"   Lidos {len(df)} registros do CSV")
    
    # Inicializar banco se necessário
    init_db()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Limpar dados anteriores
    cursor.execute('DELETE FROM consultas')
    cursor.execute('DELETE FROM pacientes')
    conn.commit()
    
    # Inserir pacientes únicos
    pacientes = df[['paciente_id', 'nome', 'faixa_etaria', 'tipo_pagamento', 
                    'faltas_anteriores', 'taxa_historica', 'tempo_como_paciente']].drop_duplicates('paciente_id')
    
    for _, paciente in pacientes.iterrows():
        cursor.execute('''
            INSERT INTO pacientes (id, nome, faixa_etaria, tipo_pagamento, 
                                  faltas_anteriores, taxa_historica, tempo_como_paciente)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            paciente['paciente_id'],
            paciente['nome'],
            paciente['faixa_etaria'],
            paciente['tipo_pagamento'],
            int(paciente['faltas_anteriores']),
            float(paciente['taxa_historica']),
            int(paciente['tempo_como_paciente'])
        ))
    
    print(f"   ✓ {len(pacientes)} pacientes inseridos")
    
    # Inserir consultas
    for _, consulta in df.iterrows():
        cursor.execute('''
            INSERT INTO consultas (paciente_id, data, horario, dia_semana, turno,
                                  procedimento, antecedencia_dias, e_retorno,
                                  n_remarcacoes, proximo_feriado, compareceu)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            consulta['paciente_id'],
            consulta['data'],
            consulta['horario'],
            consulta['dia_semana'],
            consulta['turno'],
            consulta['procedimento'],
            int(consulta['antecedencia_dias']),
            int(consulta['e_retorno']),
            int(consulta['n_remarcacoes']),
            int(consulta['proximo_feriado']),
            int(consulta['compareceu'])
        ))
    
    print(f"   ✓ {len(df)} consultas inseridas")
    
    conn.commit()
    
    # Verificar dados inseridos
    cursor.execute('SELECT COUNT(*) FROM pacientes')
    n_pacientes = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM consultas')
    n_consultas = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM consultas WHERE compareceu = 0')
    n_faltas = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n[OK] Banco populado com sucesso!")
    print(f"   [STATS] Estatísticas:")
    print(f"      • Pacientes: {n_pacientes}")
    print(f"      • Consultas: {n_consultas}")
    print(f"      • Faltas: {n_faltas} ({n_faltas/n_consultas*100:.1f}%)")

if __name__ == '__main__':
    popular_banco()
