import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from config import Config
from app import create_app


def _db_tem_dados(db_path):
    if not Path(db_path).exists():
        return False
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consultas'")
        if not cursor.fetchone():
            conn.close()
            return False
        cursor.execute("SELECT COUNT(*) FROM consultas")
        total = cursor.fetchone()[0]
        conn.close()
        return total > 0
    except Exception:
        return False


def _executar_modulo(modulo):
    subprocess.run([sys.executable, "-m", modulo], check=True)


def bootstrap_se_necessario():
    os.makedirs('dados', exist_ok=True)
    os.makedirs('modelo', exist_ok=True)

    if not Config.BOOTSTRAP_ON_START:
        return

    csv_exists = Path(Config.CSV_PATH).exists()
    model_exists = Path(Config.MODELO_PATH).exists()
    encoders_exists = Path(Config.ENCODERS_PATH).exists()
    db_ok = _db_tem_dados(Config.DATABASE_PATH)

    precisa_regerar = Config.BOOTSTRAP_REFRESH_DATA or not csv_exists
    precisa_treinar = Config.BOOTSTRAP_REFRESH_DATA or not (model_exists and encoders_exists)
    precisa_popular = Config.BOOTSTRAP_REFRESH_DATA or not db_ok

    if precisa_regerar:
        print("[BOOTSTRAP] Gerando dataset...")
        _executar_modulo("app.ml.gerar_dados")

    if precisa_treinar:
        print("[BOOTSTRAP] Treinando modelo...")
        _executar_modulo("app.ml.treinar")

    if precisa_popular:
        print("[BOOTSTRAP] Populando banco...")
        _executar_modulo("app.models.popular_banco")


bootstrap_se_necessario()
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=Config.DEBUG,
        host='0.0.0.0',
        port=5000
    )
