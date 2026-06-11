from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta
import hashlib
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.models.database import get_consultas_periodo, get_data_referencia_consultas, get_connection, get_consulta_por_id
from app.ml.substituicao import (
    buscar_substitutos,
    confirmar_substituicao,
    sugerir_reagendamento_inteligente,
    confirmar_reagendamento
)
from app.ml.inferencia import prever_e_classificar

bp = Blueprint('reorganizacao', __name__, url_prefix='/reorganizacao')


def _mascarar_telefone(paciente_id):
    digest = hashlib.sha256(str(paciente_id).encode('utf-8')).hexdigest()
    ddd = int(digest[:2], 16) % 90 + 10
    final = int(digest[-4:], 16) % 10000
    return f'({ddd}) 9****-{final:04d}'

@bp.route('/')
def index():
    """Lista consultas de alto risco para os próximos dias com opção de ação."""
    
    hoje_dt = datetime.now().date()
    data_inicio = hoje_dt.strftime('%Y-%m-%d')
    data_fim = (hoje_dt + timedelta(days=14)).strftime('%Y-%m-%d')
    consultas_periodo = get_consultas_periodo(data_inicio, data_fim)
    periodo_label = f'{data_inicio} a {data_fim}'

    if not consultas_periodo:
        data_base = get_data_referencia_consultas(data_inicio)
        if data_base:
            data_base_dt = datetime.strptime(data_base, '%Y-%m-%d').date()
            data_fim_base = (data_base_dt + timedelta(days=14)).strftime('%Y-%m-%d')
            consultas_periodo = get_consultas_periodo(data_base, data_fim_base)
            periodo_label = f'{data_base} a {data_fim_base}'

    consultas_com_risco = []
    for consulta in consultas_periodo:
        try:
            consulta_dict = dict(consulta)
            # Preparar dados para predição
            dados_consulta = {
                'faixa_etaria': consulta_dict.get('faixa_etaria', '36-60'),
                'tipo_pagamento': consulta_dict.get('tipo_pagamento', 'Convênio'),
                'faltas_anteriores': consulta_dict.get('faltas_anteriores', 0),
                'taxa_historica': consulta_dict.get('taxa_historica', 0.0),
                'tempo_como_paciente': consulta_dict.get('tempo_como_paciente', 12),
                'fumante': consulta_dict.get('fumante', 0),
                'doenca_cronica': consulta_dict.get('doenca_cronica', 0),
                'complexidade_tratamento': consulta_dict.get('complexidade_tratamento', 'Baixa'),
                'dia_semana': consulta_dict['dia_semana'],
                'turno': consulta_dict['turno'],
                'procedimento': consulta_dict['procedimento'],
                'antecedencia_dias': consulta_dict['antecedencia_dias'],
                'e_retorno': consulta_dict['e_retorno'],
                'n_remarcacoes': consulta_dict['n_remarcacoes'],
                'proximo_feriado': consulta_dict['proximo_feriado'],
                'condicao_clima': consulta_dict.get('condicao_clima', 'ensolarado'),
                'temperatura': consulta_dict.get('temperatura', 25)
            }
            
            risco = prever_e_classificar(dados_consulta)
            consulta_dict['risco'] = risco
            consultas_com_risco.append(consulta_dict)
            
        except Exception as e:
            print(f"Erro ao calcular risco: {e}")
            continue
    consultas_com_risco.sort(key=lambda x: x['risco']['probabilidade'], reverse=True)
    consultas_alto_risco = [c for c in consultas_com_risco if c['risco']['probabilidade_decimal'] >= 0.6]
    consultas_monitoramento = [c for c in consultas_com_risco if c['risco']['probabilidade_decimal'] < 0.6][:10]

    return render_template(
        'reorganizacao.html',
        consultas=consultas_alto_risco if consultas_alto_risco else consultas_monitoramento,
        data=periodo_label,
        mostrando_monitoramento=not bool(consultas_alto_risco),
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
        
        return jsonify({
            'sucesso': True,
            'consulta': {
                'id': consulta['id'],
                'paciente': consulta['nome'],
                'data': consulta['data'],
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


@bp.route('/contato/<int:consulta_id>')
def contato_consulta(consulta_id):
    """Retorna contato mascarado do paciente da consulta."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.id, p.id AS paciente_id, p.nome
            FROM consultas c
            JOIN pacientes p ON c.paciente_id = p.id
            WHERE c.id = ?
        ''', (consulta_id,))
        consulta = cursor.fetchone()
        conn.close()

        if not consulta:
            return jsonify({'sucesso': False, 'mensagem': 'Consulta não encontrada'}), 404

        telefone_mascarado = _mascarar_telefone(consulta['paciente_id'])
        return jsonify({
            'sucesso': True,
            'paciente': {
                'id': consulta['paciente_id'],
                'nome': consulta['nome']
            },
            'telefone_mascarado': telefone_mascarado
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao buscar contato: {str(e)}'}), 500


@bp.route('/confirmar-presenca', methods=['POST'])
def confirmar_presenca_route():
    """Registra confirmação de presença do paciente."""
    try:
        consulta_id = int(request.form.get('consulta_id'))
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM consultas WHERE id = ?', (consulta_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'sucesso': False, 'mensagem': 'Consulta não encontrada'}), 404

        cursor.execute('''
            UPDATE consultas
            SET confirmacao_presenca = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (consulta_id,))
        conn.commit()
        conn.close()
        return jsonify({'sucesso': True, 'mensagem': 'Presença confirmada com sucesso.'})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao confirmar presença: {str(e)}'}), 500


@bp.route('/reagendamento/<int:consulta_id>')
def sugerir_reagendamento_route(consulta_id):
    """Sugere novas janelas de horário para reduzir risco de falta."""
    try:
        consulta = get_consulta_por_id(consulta_id)
        if not consulta:
            return jsonify({'sucesso': False, 'mensagem': 'Consulta não encontrada'}), 404

        paciente = {
            'id': consulta['paciente_id'],
            'nome': consulta['nome']
        }
        telefone_mascarado = _mascarar_telefone(consulta['paciente_id'])
        opcoes = sugerir_reagendamento_inteligente(consulta_id=consulta_id, janela_dias=21, max_opcoes=5)
        return jsonify({
            'sucesso': True,
            'opcoes': opcoes,
            'paciente': paciente,
            'telefone_mascarado': telefone_mascarado
        })
    except ValueError as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 400
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao sugerir reagendamento: {str(e)}'}), 500


@bp.route('/confirmar-reagendamento', methods=['POST'])
def confirmar_reagendamento_route():
    """Confirma o reagendamento para data/hora sugeridos."""
    try:
        consulta_id = int(request.form.get('consulta_id'))
        data = request.form.get('data')
        horario = request.form.get('horario')
        resultado = confirmar_reagendamento(consulta_id=consulta_id, nova_data=data, novo_horario=horario)
        status = 200 if resultado['sucesso'] else 400
        return jsonify(resultado), status
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao confirmar reagendamento: {str(e)}'}), 500
