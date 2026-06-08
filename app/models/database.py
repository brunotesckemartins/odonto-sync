import sqlite3
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config

_schema_checked = False


def _ensure_schema(conn):
    global _schema_checked
    if _schema_checked:
        return

    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consultas'")
    if not cursor.fetchone():
        return

    cursor.execute('PRAGMA table_info(consultas)')
    colunas = {row[1] for row in cursor.fetchall()}

    if 'status_reorganizacao' not in colunas:
        cursor.execute("ALTER TABLE consultas ADD COLUMN status_reorganizacao TEXT DEFAULT 'pendente'")
    if 'confirmacao_presenca' not in colunas:
        cursor.execute("ALTER TABLE consultas ADD COLUMN confirmacao_presenca INTEGER DEFAULT 0")

    conn.commit()
    _schema_checked = True


def get_connection():
    """Cria e retorna uma conexão com o banco SQLite"""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Permite acessar colunas por nome
    _ensure_schema(conn)
    return conn

def init_db():
    """Inicializa o banco de dados criando as tabelas necessárias"""
    
    print("🗄️  Inicializando banco de dados...")
    
    # Garantir que o diretório existe
    os.makedirs(Config.DADOS_DIR, exist_ok=True)
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Tabela de pacientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            id TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            faixa_etaria TEXT NOT NULL,
            tipo_pagamento TEXT NOT NULL,
            faltas_anteriores INTEGER DEFAULT 0,
            taxa_historica REAL DEFAULT 0.0,
            tempo_como_paciente INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tabela de consultas/agendamentos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id TEXT NOT NULL,
            data DATE NOT NULL,
            horario TEXT NOT NULL,
            dia_semana TEXT NOT NULL,
            turno TEXT NOT NULL,
            procedimento TEXT NOT NULL,
            antecedencia_dias INTEGER NOT NULL,
            e_retorno INTEGER DEFAULT 0,
            n_remarcacoes INTEGER DEFAULT 0,
            proximo_feriado INTEGER DEFAULT 0,
            compareceu INTEGER,
            risco_calculado REAL,
            status_reorganizacao TEXT DEFAULT 'pendente',
            confirmacao_presenca INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    ''')
    
    # Índices para melhorar performance de queries
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_consultas_data ON consultas(data)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_consultas_paciente ON consultas(paciente_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_consultas_compareceu ON consultas(compareceu)')
    
    conn.commit()
    conn.close()
    
    print("[OK] Banco de dados inicializado com sucesso!")
    print(f"   Localização: {Config.DATABASE_PATH}")

def limpar_dados():
    """Limpa todas as tabelas do banco (útil para reprocessamento)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM consultas')
    cursor.execute('DELETE FROM pacientes')
    
    conn.commit()
    conn.close()
    
    print("🧹 Dados do banco limpos")

def get_paciente(paciente_id):
    """Busca um paciente por ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM pacientes WHERE id = ?', (paciente_id,))
    paciente = cursor.fetchone()
    
    conn.close()
    return paciente

def listar_pacientes_para_simulacao(limit=500):
    """Lista pacientes com metadados para seleção no simulador"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.id, p.nome, p.faixa_etaria, p.tipo_pagamento,
               p.faltas_anteriores, p.taxa_historica, p.tempo_como_paciente,
               MAX(c.data) AS ultima_data
        FROM pacientes p
        LEFT JOIN consultas c ON c.paciente_id = p.id
        GROUP BY p.id
        ORDER BY p.nome ASC
        LIMIT ?
    ''', (limit,))

    pacientes = cursor.fetchall()
    conn.close()
    return pacientes

def get_ultima_consulta_paciente(paciente_id):
    """Retorna a consulta mais recente de um paciente"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, paciente_id, data, horario, dia_semana, turno, procedimento,
               antecedencia_dias, e_retorno, n_remarcacoes, proximo_feriado
        FROM consultas
        WHERE paciente_id = ?
        ORDER BY data DESC, horario DESC
        LIMIT 1
    ''', (paciente_id,))

    consulta = cursor.fetchone()
    conn.close()
    return consulta

def get_proxima_consulta_paciente(paciente_id, data_referencia):
    """Retorna a próxima consulta (>= data_referencia) de um paciente."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, paciente_id, data, horario, dia_semana, turno, procedimento,
               antecedencia_dias, e_retorno, n_remarcacoes, proximo_feriado
        FROM consultas
        WHERE paciente_id = ? AND data >= ?
        ORDER BY data ASC, horario ASC
        LIMIT 1
    ''', (paciente_id, data_referencia))

    consulta = cursor.fetchone()
    conn.close()
    return consulta

def get_consultas_do_dia(data):
    """Busca todas as consultas de uma data específica"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores,
               p.taxa_historica, p.tempo_como_paciente
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.data = ? AND (c.status_reorganizacao IS NULL OR c.status_reorganizacao != 'reorganizada')
        ORDER BY c.horario
    ''', (data,))
    
    consultas = cursor.fetchall()
    conn.close()
    
    return consultas

def get_consultas_alto_risco(data, threshold=0.6):
    """Busca consultas com alto risco de falta em uma data"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores,
               p.taxa_historica, p.tempo_como_paciente
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.data = ? AND c.risco_calculado >= ?
        ORDER BY c.risco_calculado DESC
    ''', (data, threshold))
    
    consultas = cursor.fetchall()
    conn.close()
    
    return consultas

def get_consultas_periodo(data_inicio, data_fim):
    """Busca consultas de um período com dados completos de paciente."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores,
               p.taxa_historica, p.tempo_como_paciente
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.data BETWEEN ? AND ? AND (c.status_reorganizacao IS NULL OR c.status_reorganizacao != 'reorganizada')
        ORDER BY c.data ASC, c.horario ASC
    ''', (data_inicio, data_fim))

    consultas = cursor.fetchall()
    conn.close()
    return consultas


def get_consulta_por_id(consulta_id):
    """Busca uma consulta com dados de paciente por ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores,
               p.taxa_historica, p.tempo_como_paciente
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.id = ?
    ''', (consulta_id,))

    consulta = cursor.fetchone()
    conn.close()
    return consulta

def get_data_referencia_consultas(data_referencia):
    """
    Retorna a data mais próxima com consultas.
    Prioriza data igual ou futura; se não houver, usa a última passada.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT MIN(data) AS data_ref FROM consultas WHERE data >= ?', (data_referencia,))
    row = cursor.fetchone()
    if row and row['data_ref']:
        conn.close()
        return row['data_ref']

    cursor.execute('SELECT MAX(data) AS data_ref FROM consultas WHERE data < ?', (data_referencia,))
    row = cursor.fetchone()
    conn.close()
    return row['data_ref'] if row else None

def atualizar_risco_consulta(consulta_id, risco):
    """Atualiza o risco calculado de uma consulta"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        UPDATE consultas 
        SET risco_calculado = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (risco, consulta_id))
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    # Se executado diretamente, inicializa o banco
    init_db()
