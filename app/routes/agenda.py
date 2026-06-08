from flask import Blueprint, render_template
from datetime import datetime
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.models.database import get_consultas_do_dia, get_data_referencia_consultas, get_consulta_por_id, get_connection
import hashlib
from app.ml.inferencia import prever_e_classificar

bp = Blueprint('agenda', __name__)

@bp.route('/')
def index():
    """
    Página principal: agenda do dia com risco calculado por consulta.
    """
    
    # Data de hoje
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    data_referencia = hoje
    consultas = get_consultas_do_dia(data_referencia)
    
    # Se não houver agenda hoje, buscar a data mais próxima com consultas reais
    if not consultas:
        data_disponivel = get_data_referencia_consultas(hoje)
        if data_disponivel:
            data_referencia = data_disponivel
            consultas = get_consultas_do_dia(data_referencia)

    if not consultas:
        return render_template(
            'agenda.html',
            consultas=[],
            stats={'total': 0, 'alto_risco': 0, 'medio_risco': 0, 'baixo_risco': 0},
            data=hoje,
            active_page='agenda'
        )
    
    # Calcular risco para cada consulta
    consultas_com_risco = []
    stats = {'total': 0, 'alto_risco': 0, 'medio_risco': 0, 'baixo_risco': 0}
    
    for consulta in consultas:
        try:
            consulta_dict = dict(consulta)
            # Preparar dados para predição
            dados_consulta = {
                'faixa_etaria': consulta_dict.get('faixa_etaria', '36-60'),
                'tipo_pagamento': consulta_dict.get('tipo_pagamento', 'Convênio'),
                'faltas_anteriores': consulta_dict.get('faltas_anteriores', 0),
                'taxa_historica': consulta_dict.get('taxa_historica', 0.0),
                'tempo_como_paciente': consulta_dict.get('tempo_como_paciente', 12),
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
            
            # Calcular risco
            risco = prever_e_classificar(dados_consulta)
            
            # Adicionar risco aos dados da consulta
            consulta_dict['risco'] = risco
            consultas_com_risco.append(consulta_dict)
            
            # Atualizar estatísticas
            stats['total'] += 1
            if risco['categoria'] == 'Alto':
                stats['alto_risco'] += 1
            elif risco['categoria'] == 'Médio':
                stats['medio_risco'] += 1
            else:
                stats['baixo_risco'] += 1
                
        except Exception as e:
            print(f"Erro ao calcular risco: {e}")
            # Continuar mesmo com erro
            consulta_dict = dict(consulta)
            consulta_dict['risco'] = {
                'probabilidade': 50.0,
                'categoria': 'Médio',
                'cor': 'warning',
                'recomendacao': 'Erro ao calcular risco'
            }
            consultas_com_risco.append(consulta_dict)
            stats['total'] += 1
            stats['medio_risco'] += 1
    
    # Ordenar por probabilidade decrescente (maior risco primeiro)
    consultas_com_risco.sort(key=lambda x: x['risco']['probabilidade'], reverse=True)
    
    return render_template(
        'agenda.html',
        consultas=consultas_com_risco,
        stats=stats,
        data=data_referencia,
        active_page='agenda'
    )


@bp.route('/contato/<int:consulta_id>')
def contato_agenda(consulta_id):
    """Retorna contato mascarado do paciente da consulta."""
    try:
        consulta = get_consulta_por_id(consulta_id)
        if not consulta:
            return {
                'sucesso': False,
                'mensagem': 'Consulta não encontrada'
            }, 404

        digest = hashlib.sha256(str(consulta['paciente_id']).encode('utf-8')).hexdigest()
        ddd = int(digest[:2], 16) % 90 + 10
        final = int(digest[-4:], 16) % 10000
        telefone_mascarado = f'({ddd}) 9****-{final:04d}'
        return {
            'sucesso': True,
            'paciente': {
                'id': consulta['paciente_id'],
                'nome': consulta['nome']
            },
            'telefone_mascarado': telefone_mascarado,
            'nota_lgpd': 'Contato exibido de forma parcial para confirmação prévia.'
        }
    except Exception as e:
        return {
            'sucesso': False,
            'mensagem': f'Erro ao buscar contato: {str(e)}'
        }, 500


@bp.route('/confirmar-presenca', methods=['POST'])
def confirmar_presenca_agenda():
    """Registra confirmação de presença do paciente."""
    try:
        consulta_id = int(request.form.get('consulta_id'))
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM consultas WHERE id = ?', (consulta_id,))
        if not cursor.fetchone():
            conn.close()
            return {
                'sucesso': False,
                'mensagem': 'Consulta não encontrada'
            }, 404

        cursor.execute('''
            UPDATE consultas
            SET confirmacao_presenca = 1, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (consulta_id,))
        conn.commit()
        conn.close()
        return {
            'sucesso': True,
            'mensagem': 'Presença confirmada com sucesso.'
        }
    except Exception as e:
        return {
            'sucesso': False,
            'mensagem': f'Erro ao confirmar presença: {str(e)}'
        }, 500
