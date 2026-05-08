from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.ml.inferencia import prever_e_classificar
from app.models.database import (
    get_paciente,
    get_ultima_consulta_paciente,
    get_proxima_consulta_paciente,
    listar_pacientes_para_simulacao
)

bp = Blueprint('simulacao', __name__, url_prefix='/simular')

@bp.route('/', methods=['GET'])
def formulario():
    """Renderiza o formulário de simulação"""
    pacientes = listar_pacientes_para_simulacao()
    return render_template(
        'simulacao.html',
        active_page='simulacao',
        pacientes=pacientes
    )

@bp.route('/', methods=['POST'])
def simular():
    """Processa a simulação e retorna o resultado"""
    
    try:
        paciente_id = request.form.get('paciente_id', '').strip() or None
        hoje = datetime.now()
        paciente = get_paciente(paciente_id) if paciente_id else None
        ultima_consulta = get_ultima_consulta_paciente(paciente_id) if paciente_id else None
        proxima_consulta = get_proxima_consulta_paciente(paciente_id, hoje.strftime('%Y-%m-%d')) if paciente_id else None

        dados_base = {
            'faixa_etaria': paciente['faixa_etaria'] if paciente else '36-60',
            'tipo_pagamento': paciente['tipo_pagamento'] if paciente else 'Convênio',
            'faltas_anteriores': int(paciente['faltas_anteriores']) if paciente else 0,
            'taxa_historica': float(paciente['taxa_historica']) if paciente else 0.0,
            'tempo_como_paciente': int(paciente['tempo_como_paciente']) if paciente else 12,
            'dia_semana': hoje.strftime('%A'),
            'turno': 'Tarde',
            'procedimento': 'Consulta',
            'antecedencia_dias': 7,
            'e_retorno': 0,
            'n_remarcacoes': 0,
            'proximo_feriado': 0,
            'condicao_clima': 'ensolarado',
            'temperatura': 25
        }

        if ultima_consulta:
            dados_base.update({
                'dia_semana': ultima_consulta['dia_semana'],
                'turno': ultima_consulta['turno'],
                'procedimento': ultima_consulta['procedimento'],
                'antecedencia_dias': int(ultima_consulta['antecedencia_dias']),
                'e_retorno': int(ultima_consulta['e_retorno']),
                'n_remarcacoes': int(ultima_consulta['n_remarcacoes']),
                'proximo_feriado': int(ultima_consulta['proximo_feriado'])
            })

        def _to_int(campo, padrao):
            valor = request.form.get(campo, None)
            if valor is None or valor == '':
                return int(padrao)
            return int(valor)

        def _to_float(campo, padrao):
            valor = request.form.get(campo, None)
            if valor is None or valor == '':
                return float(padrao)
            return float(valor)

        def _taxa_percentual_para_decimal(campo, padrao_decimal):
            valor_percentual = _to_float(campo, float(padrao_decimal) * 100.0)
            valor_percentual = min(100.0, max(0.0, valor_percentual))
            return valor_percentual / 100.0

        # Coletar dados do formulário
        dados_consulta = {
            'faixa_etaria': request.form.get('faixa_etaria', dados_base['faixa_etaria']),
            'tipo_pagamento': request.form.get('tipo_pagamento', dados_base['tipo_pagamento']),
            'faltas_anteriores': max(0, _to_int('faltas_anteriores', dados_base['faltas_anteriores'])),
            'taxa_historica': _taxa_percentual_para_decimal('taxa_historica', dados_base['taxa_historica']),
            'tempo_como_paciente': max(1, _to_int('tempo_como_paciente', dados_base['tempo_como_paciente'])),
            'dia_semana': request.form.get('dia_semana', dados_base['dia_semana']),
            'turno': request.form.get('turno', dados_base['turno']),
            'procedimento': request.form.get('procedimento', dados_base['procedimento']),
            'antecedencia_dias': max(1, _to_int('antecedencia_dias', dados_base['antecedencia_dias'])),
            'e_retorno': 1 if _to_int('e_retorno', dados_base['e_retorno']) == 1 else 0,
            'n_remarcacoes': max(0, _to_int('n_remarcacoes', dados_base['n_remarcacoes'])),
            'proximo_feriado': 1 if _to_int('proximo_feriado', dados_base['proximo_feriado']) == 1 else 0,
            'condicao_clima': request.form.get('condicao_clima', 'ensolarado'),
            'temperatura': min(45, max(10, _to_int('temperatura', 25)))
        }
        
        # Calcular risco
        resultado = prever_e_classificar(dados_consulta)
        
        # Adicionar dados da consulta ao resultado
        resultado['dados_consulta'] = dados_consulta
        resultado['sucesso'] = True
        if paciente:
            resultado['paciente'] = {'id': paciente['id'], 'nome': paciente['nome']}
            resultado['base_origem'] = 'paciente_base'
            if proxima_consulta:
                resultado['consulta_reagendavel'] = {
                    'id': proxima_consulta['id'],
                    'data': proxima_consulta['data'],
                    'horario': proxima_consulta['horario'],
                    'procedimento': proxima_consulta['procedimento']
                }
        
        pacientes = listar_pacientes_para_simulacao()
        return render_template('simulacao.html', 
                             resultado=resultado, 
                             active_page='simulacao',
                             dados=dados_consulta,
                             pacientes=pacientes,
                             paciente_selecionado=paciente_id)
        
    except Exception as e:
        pacientes = listar_pacientes_para_simulacao()
        return render_template('simulacao.html', 
                              erro=str(e), 
                              active_page='simulacao',
                              pacientes=pacientes)

@bp.route('/paciente/<paciente_id>', methods=['GET'])
def carregar_paciente(paciente_id):
    """Retorna dados do paciente e da última consulta para pré-preenchimento"""
    paciente = get_paciente(paciente_id)
    if not paciente:
        return jsonify({'sucesso': False, 'erro': 'Paciente não encontrado'}), 404

    consulta = get_ultima_consulta_paciente(paciente_id)
    hoje = datetime.now()

    payload = {
        'faixa_etaria': paciente['faixa_etaria'],
        'tipo_pagamento': paciente['tipo_pagamento'],
        'faltas_anteriores': int(paciente['faltas_anteriores']),
        'taxa_historica': round(float(paciente['taxa_historica']) * 100.0, 1),
        'tempo_como_paciente': int(paciente['tempo_como_paciente']),
        'dia_semana': hoje.strftime('%A'),
        'turno': 'Tarde',
        'procedimento': 'Consulta',
        'antecedencia_dias': 7,
        'e_retorno': 0,
        'n_remarcacoes': 0,
        'proximo_feriado': 0,
        'condicao_clima': 'ensolarado',
        'temperatura': 25
    }

    if consulta:
        payload.update({
            'dia_semana': consulta['dia_semana'],
            'turno': consulta['turno'],
            'procedimento': consulta['procedimento'],
            'antecedencia_dias': int(consulta['antecedencia_dias']),
            'e_retorno': int(consulta['e_retorno']),
            'n_remarcacoes': int(consulta['n_remarcacoes']),
            'proximo_feriado': int(consulta['proximo_feriado'])
        })

    return jsonify({
        'sucesso': True,
        'paciente': {
            'id': paciente['id'],
            'nome': paciente['nome']
        },
        'dados': payload
    })
