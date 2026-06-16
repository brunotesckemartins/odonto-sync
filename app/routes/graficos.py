from flask import Blueprint, render_template
import matplotlib
matplotlib.use('Agg')  # Backend sem GUI
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import io
import base64
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config
from app.models.database import get_connection
import joblib

bp = Blueprint('graficos', __name__, url_prefix='/graficos')

# Configurar estilo dos gráficos
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (8, 6)
plt.rcParams['font.size'] = 10

@bp.route('/')
def index():
    """Página de análise exploratória com gráficos"""
    
    try:
        # Carregar dados do banco SQLite
        conn = get_connection()
        df = pd.read_sql_query('''
            SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores,
                   p.taxa_historica, p.tempo_como_paciente,
                   p.fumante, p.doenca_cronica, p.complexidade_tratamento
            FROM consultas c
            JOIN pacientes p ON c.paciente_id = p.id
            WHERE c.compareceu IS NOT NULL
        ''', conn)
        conn.close()
        
        # Fallback caso o banco esteja vazio de histórico
        if df.empty:
            df = pd.read_csv(Config.CSV_PATH)
        
        # Gerar gráficos
        graficos = {
            'falta_por_dia': _grafico_falta_por_dia(df),
            'falta_por_turno': _grafico_falta_por_turno(df),
            'importancia_features': _grafico_importancia_features(),
            'distribuicao_target': _grafico_distribuicao_target(df)
        }
        
        # Estatísticas gerais
        stats = {
            'total_registros': len(df),
            'taxa_falta': round((1 - df['compareceu'].mean()) * 100, 1),
            'total_faltas': (1 - df['compareceu']).sum(),
            'total_compareceu': df['compareceu'].sum()
        }
        
        return render_template(
            'graficos.html',
            graficos=graficos,
            stats=stats,
            active_page='graficos'
        )
        
    except Exception as e:
        return render_template(
            'graficos.html',
            erro=str(e),
            active_page='graficos'
        )

def _grafico_falta_por_dia(df):
    """Gráfico: Taxa de falta por dia da semana"""
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Calcular taxa de falta por dia
    falta_por_dia = df.groupby('dia_semana').agg({
        'compareceu': lambda x: (1 - x.mean()) * 100
    }).reset_index()
    
    # Ordenar dias da semana
    dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    falta_por_dia['dia_semana'] = pd.Categorical(
        falta_por_dia['dia_semana'], 
        categories=dias_ordem, 
        ordered=True
    )
    falta_por_dia = falta_por_dia.sort_values('dia_semana')
    
    # Traduzir nomes dos dias
    dias_pt = {
        'Monday': 'Segunda',
        'Tuesday': 'Terça',
        'Wednesday': 'Quarta',
        'Thursday': 'Quinta',
        'Friday': 'Sexta',
        'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    falta_por_dia['dia_pt'] = falta_por_dia['dia_semana'].map(dias_pt)
    
    # Criar gráfico
    bars = ax.bar(falta_por_dia['dia_pt'], falta_por_dia['compareceu'], 
                  color='#3498db', alpha=0.8, edgecolor='black')
    
    # Destacar segunda-feira (maior risco)
    bars[0].set_color('#e74c3c')
    
    ax.set_xlabel('Dia da Semana', fontsize=12, fontweight='bold')
    ax.set_ylabel('Taxa de Falta (%)', fontsize=12, fontweight='bold')
    ax.set_title('Taxa de Falta por Dia da Semana', fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    return _fig_to_base64(fig)

def _grafico_falta_por_turno(df):
    """Gráfico: Taxa de falta por turno"""
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Calcular taxa de falta por turno
    falta_por_turno = df.groupby('turno').agg({
        'compareceu': lambda x: (1 - x.mean()) * 100
    }).reset_index()
    
    # Ordenar turnos
    turnos_ordem = ['Manhã', 'Tarde', 'Noite']
    falta_por_turno['turno'] = pd.Categorical(
        falta_por_turno['turno'],
        categories=turnos_ordem,
        ordered=True
    )
    falta_por_turno = falta_por_turno.sort_values('turno')
    
    # Criar gráfico
    colors = ['#3498db', '#f39c12', '#e74c3c']
    bars = ax.bar(falta_por_turno['turno'], falta_por_turno['compareceu'],
                  color=colors, alpha=0.8, edgecolor='black')
    
    ax.set_xlabel('Turno', fontsize=12, fontweight='bold')
    ax.set_ylabel('Taxa de Falta (%)', fontsize=12, fontweight='bold')
    ax.set_title('Taxa de Falta por Turno', fontsize=14, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    return _fig_to_base64(fig)

def _grafico_importancia_features():
    """Gráfico: Importância das features do modelo"""
    
    try:
        # Carregar modelo
        modelo = joblib.load(Config.MODELO_PATH)
        
        if hasattr(modelo, 'feature_importances_'):
            fig, ax = plt.subplots(figsize=(10, 8))
            
            # Features
            feature_names = [
                'Faixa Etária', 'Tipo Pagamento', 'Faltas Anteriores',
                'Taxa Histórica', 'Tempo Paciente', 'Dia Semana',
                'Turno', 'Procedimento', 'Antecedência', 'É Retorno',
                'Remarcações', 'Próx. Feriado', 'Condição Clima', 'Temperatura'
            ]
            
            # Importâncias
            importances = modelo.feature_importances_
            
            # Criar DataFrame e ordenar
            df_imp = pd.DataFrame({
                'feature': feature_names,
                'importance': importances
            }).sort_values('importance', ascending=True)
            
            # Criar gráfico horizontal
            bars = ax.barh(df_imp['feature'], df_imp['importance'],
                          color='#2ecc71', alpha=0.8, edgecolor='black')
            
            # Destacar top 3
            for i in range(-3, 0):
                bars[i].set_color('#e67e22')
            
            ax.set_xlabel('Importância', fontsize=12, fontweight='bold')
            ax.set_ylabel('Feature', fontsize=12, fontweight='bold')
            ax.set_title('Importância das Features no Modelo', fontsize=14, fontweight='bold', pad=20)
            ax.grid(axis='x', alpha=0.3)
            plt.tight_layout()
            
            return _fig_to_base64(fig)
        else:
            return None
            
    except Exception as e:
        print(f"Erro ao gerar gráfico de importância: {e}")
        return None

def _grafico_distribuicao_target(df):
    """Gráfico: Distribuição do target (compareceu vs faltou)"""
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Calcular distribuição
    compareceu = df['compareceu'].sum()
    faltou = len(df) - compareceu
    
    # Criar gráfico de pizza
    sizes = [compareceu, faltou]
    labels = [f'Compareceu\n({compareceu})', f'Faltou\n({faltou})']
    colors = ['#2ecc71', '#e74c3c']
    explode = (0, 0.1)  # Destacar "Faltou"
    
    ax.pie(sizes, explode=explode, labels=labels, colors=colors,
           autopct='%1.1f%%', shadow=True, startangle=90,
           textprops={'fontsize': 12, 'fontweight': 'bold'})
    
    ax.set_title('Distribuição: Compareceu vs Faltou', 
                fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    
    return _fig_to_base64(fig)

def _fig_to_base64(fig):
    """Converte figura matplotlib para base64"""
    
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return img_base64
