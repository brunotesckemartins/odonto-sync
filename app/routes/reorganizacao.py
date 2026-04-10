from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.models.database import get_consultas_alto_risco, get_connection
from app.ml.substituicao import buscar_substitutos, confirmar_substituicao
from app.ml.inferencia import prever_e_classificar

bp = Blueprint('reorganizacao', __name__, url_prefix='/reorganizacao')

@bp.route('/')
def index():
    """Lista consultas de alto risco do dia com opção de buscar substitutos"""
    
    # Data de hoje
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    # Buscar consultas de alto risco (>= 60%)
    consultas_alto_risco = get_consultas_alto_risco(hoje, threshold=0.6)
    
    # Se não houver consultas, usar dados demo
    if not consultas_alto_risco:
        consultas_alto_risco = _gerar_demo_alto_risco()
    
    # Calcular risco para cada consulta
    consultas_com_risco = []
    
    for consulta in consultas_alto_risco:
        try:
            # Preparar dados para predição
            dados_consulta = {
                'faixa_etaria': consulta.get('faixa_etaria', '18-35'),
                'tipo_pagamento': consulta.get('tipo_pagamento', 'Convênio'),
                'faltas_anteriores': consulta.get('faltas_anteriores', 0),
                'taxa_historica': consulta.get('taxa_historica', 0.0),
                'tempo_como_paciente': consulta.get('tempo_como_paciente', 12),
                'dia_semana': consulta['dia_semana'],
                'turno': consulta['turno'],
                'procedimento': consulta['procedimento'],
                'antecedencia_dias': consulta['antecedencia_dias'],
                'e_retorno': consulta['e_retorno'],
                'n_remarcacoes': consulta['n_remarcacoes'],
                'proximo_feriado': consulta['proximo_feriado']
            }
            
            # Calcular risco
            risco = prever_e_classificar(dados_consulta)
            
            # Adicionar risco aos dados
            consulta_dict = dict(consulta)
            consulta_dict['risco'] = risco
            consultas_com_risco.append(consulta_dict)
            
        except Exception as e:
            print(f"Erro ao calcular risco: {e}")
            continue
    
    return render_template(
        'reorganizacao.html',
        consultas=consultas_com_risco,
        data=hoje,
        active_page='reorganizacao'
    )

@bp.route('/substitutos/<int:consulta_id>')
def buscar_substitutos_route(consulta_id):
    """Busca substitutos para uma consulta específica"""
    
    try:
        # Buscar informações da consulta
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.*, p.nome, p.tipo_pagamento
            FROM consultas c
            JOIN pacientes p ON c.paciente_id = p.id
            WHERE c.id = ?
        ''', (consulta_id,))
        
        consulta = cursor.fetchone()
        conn.close()
        
        if not consulta:
            return jsonify({'erro': 'Consulta não encontrada'}), 404
        
        # Buscar substitutos
        substitutos = buscar_substitutos(
            consulta_id=consulta_id,
            data=consulta['data'],
            horario=consulta['horario'],
            n=3
        )
        
        # Se não houver substitutos reais, gerar demo
        if not substitutos:
            substitutos = _gerar_substitutos_demo(consulta)
        
        return jsonify({
            'sucesso': True,
            'consulta': {
                'id': consulta['id'],
                'paciente': consulta['nome'],
                'horario': consulta['horario'],
                'procedimento': consulta['procedimento']
            },
            'substitutos': substitutos
        })
        
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@bp.route('/confirmar', methods=['POST'])
def confirmar():
    """Confirma a substituição de um paciente"""
    
    try:
        consulta_id = int(request.form.get('consulta_id'))
        paciente_id = request.form.get('paciente_id')
        data = request.form.get('data')
        horario = request.form.get('horario')
        
        resultado = confirmar_substituicao(
            consulta_id=consulta_id,
            paciente_substituto_id=paciente_id,
            data=data,
            horario=horario
        )
        
        if resultado['sucesso']:
            return jsonify({
                'sucesso': True,
                'mensagem': resultado['mensagem']
            })
        else:
            return jsonify({
                'sucesso': False,
                'mensagem': resultado['mensagem']
            }), 400
            
    except Exception as e:
        return jsonify({
            'sucesso': False,
            'mensagem': f'Erro ao confirmar substituição: {str(e)}'
        }), 500

def _gerar_demo_alto_risco():
    """Gera dados demo de consultas de alto risco"""
    
    hoje = datetime.now()
    dia_semana = hoje.strftime('%A')
    
    return [
        {
            'id': 1,
            'horario': '08:00',
            'nome': 'Maria Silva',
            'tipo_pagamento': 'SUS',
            'procedimento': 'Consulta',
            'faltas_anteriores': 3,
            'antecedencia_dias': 21,
            'dia_semana': dia_semana,
            'turno': 'Manhã',
            'e_retorno': 0,
            'n_remarcacoes': 2,
            'proximo_feriado': 1,
            'faixa_etaria': '18-35',
            'taxa_historica': 0.6,
            'tempo_como_paciente': 4,
            'data': hoje.strftime('%Y-%m-%d')
        },
        {
            'id': 3,
            'horario': '17:00',
            'nome': 'Carlos Souza',
            'tipo_pagamento': 'Convênio',
            'procedimento': 'Obturação',
            'faltas_anteriores': 4,
            'antecedencia_dias': 30,
            'dia_semana': dia_semana,
            'turno': 'Tarde',
            'e_retorno': 0,
            'n_remarcacoes': 3,
            'proximo_feriado': 1,
            'faixa_etaria': '18-35',
            'taxa_historica': 0.7,
            'tempo_como_paciente': 2,
            'data': hoje.strftime('%Y-%m-%d')
        }
    ]

def _gerar_substitutos_demo(consulta):
    """Gera substitutos demo para demonstração"""
    
    return [
        {
            'paciente_id': 'PAC9001',
            'nome': 'João Pedro Silva',
            'tipo_pagamento': 'Particular',
            'faixa_etaria': '36-60',
            'faltas_anteriores': 0,
            'probabilidade_falta': 8.5,
            'justificativa': 'Recomendado: histórico confiável, sem faltas anteriores, pagamento particular, paciente há mais de 2 anos',
            'score': 92.3
        },
        {
            'paciente_id': 'PAC9002',
            'nome': 'Ana Paula Costa',
            'tipo_pagamento': 'Particular',
            'faixa_etaria': '60+',
            'faltas_anteriores': 0,
            'probabilidade_falta': 12.3,
            'justificativa': 'Recomendado: sem faltas anteriores, pagamento particular, taxa de falta < 10%',
            'score': 88.7
        },
        {
            'paciente_id': 'PAC9003',
            'nome': 'Roberto Alves Santos',
            'tipo_pagamento': 'Convênio',
            'faixa_etaria': '36-60',
            'faltas_anteriores': 1,
            'probabilidade_falta': 18.9,
            'justificativa': 'Recomendado: histórico confiável, paciente há mais de 2 anos',
            'score': 82.1
        }
    ]
