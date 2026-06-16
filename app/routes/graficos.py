from flask import Blueprint, render_template
import pandas as pd
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config
from app.models.database import get_connection
import joblib

bp = Blueprint('graficos', __name__, url_prefix='/graficos')

@bp.route('/')
def index():
    """Página de análise exploratória com gráficos (Chart.js)"""
    
    try:
        # Carregar dados do banco SQLite
        conn = get_connection()
        df_db = pd.read_sql_query('''
            SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores,
                   p.taxa_historica, p.tempo_como_paciente,
                   p.fumante, p.doenca_cronica, p.complexidade_tratamento
            FROM consultas c
            JOIN pacientes p ON c.paciente_id = p.id
        ''', conn)
        conn.close()
        
        # Combinar com CSV para garantir dados ricos, simulando "alterações no sistema"
        df_csv = pd.read_csv(Config.CSV_PATH)
        
        # Usamos df_db, e se for pequeno completamos com dados do csv
        if len(df_db) < 50:
            df = pd.concat([df_db, df_csv], ignore_index=True)
        else:
            df = df_db

        # Precisamos de compareceu preenchido para estatísticas
        df_valido = df.dropna(subset=['compareceu']).copy()
        if df_valido.empty:
            df_valido = df_csv

        # 1. Falta por Dia
        falta_por_dia = df_valido.groupby('dia_semana').agg({
            'compareceu': lambda x: (1 - x.mean()) * 100
        }).reset_index()
        dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        falta_por_dia['dia_semana'] = pd.Categorical(falta_por_dia['dia_semana'], categories=dias_ordem, ordered=True)
        falta_por_dia = falta_por_dia.sort_values('dia_semana')
        dias_pt = {'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta', 'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'}
        
        grafico_dia = {
            'labels': [dias_pt.get(d, d) for d in falta_por_dia['dia_semana']],
            'data': falta_por_dia['compareceu'].round(1).tolist()
        }

        # 2. Falta por Turno
        falta_por_turno = df_valido.groupby('turno').agg({
            'compareceu': lambda x: (1 - x.mean()) * 100
        }).reset_index()
        turnos_ordem = ['Manhã', 'Tarde', 'Noite']
        falta_por_turno['turno'] = pd.Categorical(falta_por_turno['turno'], categories=turnos_ordem, ordered=True)
        falta_por_turno = falta_por_turno.sort_values('turno')
        
        grafico_turno = {
            'labels': falta_por_turno['turno'].tolist(),
            'data': falta_por_turno['compareceu'].round(1).tolist()
        }

        # 3. Distribuição
        compareceu_count = int(df_valido['compareceu'].sum())
        faltou_count = int(len(df_valido) - compareceu_count)
        
        grafico_dist = {
            'labels': ['Compareceu', 'Faltou'],
            'data': [compareceu_count, faltou_count]
        }

        # 4. Importância das Features (estático do modelo)
        grafico_imp = None
        try:
            modelo = joblib.load(Config.MODELO_PATH)
            if hasattr(modelo, 'feature_importances_'):
                feature_names = ['Faixa Etária', 'Tipo Pagamento', 'Faltas Anteriores', 'Taxa Histórica', 'Tempo Paciente', 'Dia Semana', 'Turno', 'Procedimento', 'Antecedência', 'É Retorno', 'Remarcações', 'Próx. Feriado', 'Condição Clima', 'Temperatura']
                importances = modelo.feature_importances_
                df_imp = pd.DataFrame({'feature': feature_names, 'importance': importances}).sort_values('importance', ascending=True).tail(5)
                grafico_imp = {
                    'labels': df_imp['feature'].tolist(),
                    'data': (df_imp['importance'] * 100).round(1).tolist()
                }
        except:
            pass

        # Estatísticas gerais
        stats = {
            'total_registros': len(df_valido),
            'taxa_falta': round((1 - df_valido['compareceu'].mean()) * 100, 1),
            'total_faltas': faltou_count,
            'total_compareceu': compareceu_count
        }
        
        return render_template(
            'graficos.html',
            grafico_dia=grafico_dia,
            grafico_turno=grafico_turno,
            grafico_dist=grafico_dist,
            grafico_imp=grafico_imp,
            stats=stats,
            active_page='graficos'
        )
        
    except Exception as e:
        return render_template(
            'graficos.html',
            erro=str(e),
            active_page='graficos'
        )
