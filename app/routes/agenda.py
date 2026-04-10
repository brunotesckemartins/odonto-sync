from flask import Blueprint, render_template, current_app
from datetime import datetime
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.models.database import get_consultas_do_dia, get_connection
from app.ml.inferencia import prever_e_classificar

bp = Blueprint('agenda', __name__)

@bp.route('/')
def index():
    """
    Página principal: agenda do dia com risco calculado por consulta.
    """
    
    # Data de hoje
    hoje = datetime.now().strftime('%Y-%m-%d')
    
    # Buscar consultas do dia
    consultas = get_consultas_do_dia(hoje)
    
    # Se não houver consultas hoje, gerar dados demo
    if not consultas:
        consultas = _gerar_consultas_demo()
    
    # Calcular risco para cada consulta
    consultas_com_risco = []
    stats = {'total': 0, 'alto_risco': 0, 'medio_risco': 0, 'baixo_risco': 0}
    
    for consulta in consultas:
        try:
            # Preparar dados para predição
            dados_consulta = {
                'faixa_etaria': consulta['faixa_etaria'],
                'tipo_pagamento': consulta['tipo_pagamento'],
                'faltas_anteriores': consulta['faltas_anteriores'],
                'taxa_historica': consulta.get('taxa_historica', 0.0),
                'tempo_como_paciente': consulta.get('tempo_como_paciente', 12),
                'dia_semana': consulta['dia_semana'],
                'turno': consulta['turno'],
                'procedimento': consulta['procedimento'],
                'antecedencia_dias': consulta['antecedencia_dias'],
                'e_retorno': consulta['e_retorno'],
                'n_remarcacoes': consulta['n_remarcacoes'],
                'proximo_feriado': consulta['proximo_feriado'],
                'condicao_clima': consulta.get('condicao_clima', 'ensolarado'),
                'temperatura': consulta.get('temperatura', 25)
            }
            
            # Calcular risco
            risco = prever_e_classificar(dados_consulta)
            
            # Adicionar risco aos dados da consulta
            consulta_dict = dict(consulta)
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
        data=hoje,
        active_page='agenda'
    )

def _gerar_consultas_demo():
    """Gera dados demo para demonstração"""
    
    from datetime import datetime
    
    hoje = datetime.now()
    dia_semana = hoje.strftime('%A')
    
    demo_data = [
        {
            'id': 1,
            'horario': '08:00',
            'nome': 'Maria Silva',
            'tipo_pagamento': 'Convênio',
            'procedimento': 'Consulta',
            'faltas_anteriores': 2,
            'antecedencia_dias': 15,
            'dia_semana': dia_semana,
            'turno': 'Manhã',
            'e_retorno': 0,
            'n_remarcacoes': 1,
            'proximo_feriado': 0,
            'faixa_etaria': '36-60',
            'taxa_historica': 0.3,
            'tempo_como_paciente': 8,
            'condicao_clima': 'nublado',
            'temperatura': 23
        },
        {
            'id': 2,
            'horario': '09:00',
            'nome': 'João Santos',
            'tipo_pagamento': 'Particular',
            'procedimento': 'Limpeza',
            'faltas_anteriores': 0,
            'antecedencia_dias': 7,
            'dia_semana': dia_semana,
            'turno': 'Manhã',
            'e_retorno': 1,
            'n_remarcacoes': 0,
            'proximo_feriado': 0,
            'faixa_etaria': '60+',
            'taxa_historica': 0.05,
            'tempo_como_paciente': 36,
            'condicao_clima': 'ensolarado',
            'temperatura': 27
        },
        {
            'id': 3,
            'horario': '10:00',
            'nome': 'Ana Costa',
            'tipo_pagamento': 'SUS',
            'procedimento': 'Obturação',
            'faltas_anteriores': 3,
            'antecedencia_dias': 21,
            'dia_semana': dia_semana,
            'turno': 'Manhã',
            'e_retorno': 0,
            'n_remarcacoes': 2,
            'proximo_feriado': 1,
            'faixa_etaria': '18-35',
            'taxa_historica': 0.5,
            'tempo_como_paciente': 4,
            'condicao_clima': 'chuvoso',
            'temperatura': 19
        },
        {
            'id': 4,
            'horario': '11:00',
            'nome': 'Pedro Oliveira',
            'tipo_pagamento': 'Particular',
            'procedimento': 'Canal',
            'faltas_anteriores': 0,
            'antecedencia_dias': 3,
            'dia_semana': dia_semana,
            'turno': 'Manhã',
            'e_retorno': 1,
            'n_remarcacoes': 0,
            'proximo_feriado': 0,
            'faixa_etaria': '36-60',
            'taxa_historica': 0.08,
            'tempo_como_paciente': 24,
            'condicao_clima': 'ensolarado',
            'temperatura': 26
        },
        {
            'id': 5,
            'horario': '14:00',
            'nome': 'Carla Mendes',
            'tipo_pagamento': 'Convênio',
            'procedimento': 'Consulta',
            'faltas_anteriores': 1,
            'antecedencia_dias': 10,
            'dia_semana': dia_semana,
            'turno': 'Tarde',
            'e_retorno': 0,
            'n_remarcacoes': 0,
            'proximo_feriado': 0,
            'faixa_etaria': '18-35',
            'taxa_historica': 0.2,
            'tempo_como_paciente': 12,
            'condicao_clima': 'ensolarado',
            'temperatura': 29
        },
        {
            'id': 6,
            'horario': '15:00',
            'nome': 'Roberto Lima',
            'tipo_pagamento': 'SUS',
            'procedimento': 'Extração',
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
            'condicao_clima': 'tempestade',
            'temperatura': 18
        },
        {
            'id': 7,
            'horario': '16:00',
            'nome': 'Lucia Ferreira',
            'tipo_pagamento': 'Particular',
            'procedimento': 'Clareamento',
            'faltas_anteriores': 0,
            'antecedencia_dias': 5,
            'dia_semana': dia_semana,
            'turno': 'Tarde',
            'e_retorno': 0,
            'n_remarcacoes': 0,
            'proximo_feriado': 0,
            'faixa_etaria': '36-60',
            'taxa_historica': 0.0,
            'tempo_como_paciente': 48,
            'condicao_clima': 'ensolarado',
            'temperatura': 28
        },
        {
            'id': 8,
            'horario': '17:00',
            'nome': 'Carlos Souza',
            'tipo_pagamento': 'Convênio',
            'procedimento': 'Consulta',
            'faltas_anteriores': 2,
            'antecedencia_dias': 14,
            'dia_semana': dia_semana,
            'turno': 'Tarde',
            'e_retorno': 0,
            'n_remarcacoes': 1,
            'proximo_feriado': 0,
            'faixa_etaria': '18-35',
            'taxa_historica': 0.35,
            'tempo_como_paciente': 6,
            'condicao_clima': 'nublado',
            'temperatura': 24
        },
        {
            'id': 9,
            'horario': '18:00',
            'nome': 'Patricia Alves',
            'tipo_pagamento': 'Particular',
            'procedimento': 'Limpeza',
            'faltas_anteriores': 0,
            'antecedencia_dias': 7,
            'dia_semana': dia_semana,
            'turno': 'Noite',
            'e_retorno': 1,
            'n_remarcacoes': 0,
            'proximo_feriado': 0,
            'faixa_etaria': '60+',
            'taxa_historica': 0.02,
            'tempo_como_paciente': 60,
            'condicao_clima': 'ensolarado',
            'temperatura': 25
        },
        {
            'id': 10,
            'horario': '19:00',
            'nome': 'Rafael Gomes',
            'tipo_pagamento': 'SUS',
            'procedimento': 'Obturação',
            'faltas_anteriores': 3,
            'antecedencia_dias': 25,
            'dia_semana': dia_semana,
            'turno': 'Noite',
            'e_retorno': 0,
            'n_remarcacoes': 2,
            'proximo_feriado': 1,
            'faixa_etaria': '0-17',
            'taxa_historica': 0.6,
            'tempo_como_paciente': 3,
            'condicao_clima': 'chuvoso',
            'temperatura': 20
        }
    ]
    
    return demo_data
