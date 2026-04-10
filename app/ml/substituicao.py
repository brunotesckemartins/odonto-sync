import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config
from app.models.database import get_connection
from app.ml.inferencia import prever_risco
from app.ml.ai_suggestions import get_ai_assistant

def buscar_substitutos(consulta_id, data, horario, n=3):
    """
    Busca pacientes substitutos para uma consulta de alto risco.
    
    Estratégia:
    1. Buscar pacientes sem consulta agendada naquele dia
    2. Calcular probabilidade de falta de cada candidato
    3. Ordenar por menor probabilidade (mais confiável)
    4. Retornar os N melhores candidatos com justificativa
    
    Args:
        consulta_id (int): ID da consulta original
        data (str): Data da consulta (YYYY-MM-DD)
        horario (str): Horário da consulta (HH:MM)
        n (int): Número de substitutos a retornar
    
    Returns:
        list: Lista de dicionários com dados dos substitutos
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Buscar informações da consulta original
    cursor.execute('''
        SELECT c.*, p.*
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.id = ?
    ''', (consulta_id,))
    
    consulta_original = cursor.fetchone()
    
    if not consulta_original:
        conn.close()
        return []
    
    # Buscar pacientes que NÃO têm consulta naquele dia
    cursor.execute('''
        SELECT DISTINCT p.*
        FROM pacientes p
        WHERE p.id NOT IN (
            SELECT paciente_id 
            FROM consultas 
            WHERE data = ?
        )
        LIMIT 50
    ''', (data,))
    
    candidatos = cursor.fetchall()
    conn.close()
    
    if not candidatos:
        return []
    
    # Calcular risco de cada candidato
    substitutos = []
    
    for candidato in candidatos:
        # Criar dados da consulta hipotética
        dados_consulta = {
            'faixa_etaria': candidato['faixa_etaria'],
            'tipo_pagamento': candidato['tipo_pagamento'],
            'faltas_anteriores': candidato['faltas_anteriores'],
            'taxa_historica': candidato['taxa_historica'],
            'tempo_como_paciente': candidato['tempo_como_paciente'],
            'dia_semana': datetime.strptime(data, '%Y-%m-%d').strftime('%A'),
            'turno': _determinar_turno(horario),
            'procedimento': consulta_original['procedimento'],
            'antecedencia_dias': 0,  # Assumir confirmação imediata
            'e_retorno': 0,
            'n_remarcacoes': 0,
            'proximo_feriado': 0
        }
        
        # Calcular probabilidade de falta
        try:
            prob_falta = prever_risco(dados_consulta)
        except:
            prob_falta = 0.5  # Fallback se houver erro
        
        # Gerar justificativa
        justificativa = _gerar_justificativa(candidato, prob_falta)
        
        # Calcular score de compatibilidade
        score = _calcular_score_compatibilidade(
            candidato, 
            consulta_original, 
            prob_falta
        )
        
        substitutos.append({
            'paciente_id': candidato['id'],
            'nome': candidato['nome'],
            'tipo_pagamento': candidato['tipo_pagamento'],
            'faixa_etaria': candidato['faixa_etaria'],
            'faltas_anteriores': candidato['faltas_anteriores'],
            'probabilidade': prob_falta,
            'probabilidade_falta': round(prob_falta * 100, 1),
            'tempo_como_paciente': candidato['tempo_como_paciente'],
            'taxa_historica': candidato['taxa_historica'],
            'compatibilidade': score,
            'justificativa': justificativa,
            'score': score
        })
    
    # Ordenar por score (maior = melhor)
    substitutos.sort(key=lambda x: x['score'], reverse=True)
    top_substitutos = substitutos[:n]
    
    # Usar IA para gerar justificativas melhores
    ai = get_ai_assistant()
    if ai.available and Config.USE_AI_SUGGESTIONS:
        original_patient = {
            'nome': consulta_original.get('nome', ''),
            'probabilidade': consulta_original.get('probabilidade', 0),
            'faltas_anteriores': consulta_original.get('faltas_anteriores', 0)
        }
        top_substitutos = ai.analyze_substitutes(
            original_patient, top_substitutos, data, horario
        )
    
    return top_substitutos

def _determinar_turno(horario):
    """Determina o turno com base no horário"""
    hora = int(horario.split(':')[0])
    
    if hora < 12:
        return 'Manhã'
    elif hora < 18:
        return 'Tarde'
    else:
        return 'Noite'

def _gerar_justificativa(candidato, prob_falta):
    """Gera justificativa para o candidato"""
    razoes = []
    
    # Taxa de falta baixa
    if prob_falta < 0.3:
        razoes.append("histórico confiável")
    
    # Sem faltas anteriores
    if candidato['faltas_anteriores'] == 0:
        razoes.append("sem faltas anteriores")
    
    # Particular (mais confiável)
    if candidato['tipo_pagamento'] == 'Particular':
        razoes.append("pagamento particular")
    
    # Paciente antigo
    if candidato['tempo_como_paciente'] > 24:
        razoes.append("paciente há mais de 2 anos")
    
    # Taxa histórica baixa
    if candidato['taxa_historica'] < 0.1:
        razoes.append("taxa de falta < 10%")
    
    if not razoes:
        razoes.append("disponível no horário")
    
    return "Recomendado: " + ", ".join(razoes)

def _calcular_score_compatibilidade(candidato, consulta_original, prob_falta):
    """
    Calcula score de compatibilidade (quanto maior, melhor).
    
    Fatores:
    - Probabilidade de falta baixa (peso 40%)
    - Sem faltas anteriores (peso 20%)
    - Tipo de pagamento confiável (peso 20%)
    - Tempo como paciente (peso 10%)
    - Taxa histórica baixa (peso 10%)
    """
    
    score = 0.0
    
    # Fator 1: Probabilidade de falta (inverso: menor prob = maior score)
    score += (1 - prob_falta) * 40
    
    # Fator 2: Faltas anteriores (inverso)
    faltas = min(candidato['faltas_anteriores'], 5)  # Cap em 5
    score += (5 - faltas) / 5 * 20
    
    # Fator 3: Tipo de pagamento
    if candidato['tipo_pagamento'] == 'Particular':
        score += 20
    elif candidato['tipo_pagamento'] == 'Convênio':
        score += 15
    else:  # SUS
        score += 10
    
    # Fator 4: Tempo como paciente (normalizado para 60 meses)
    tempo_norm = min(candidato['tempo_como_paciente'], 60) / 60
    score += tempo_norm * 10
    
    # Fator 5: Taxa histórica (inverso)
    score += (1 - candidato['taxa_historica']) * 10
    
    return round(score, 2)

def confirmar_substituicao(consulta_id, paciente_substituto_id, data, horario):
    """
    Confirma a substituição de um paciente.
    
    Args:
        consulta_id (int): ID da consulta original
        paciente_substituto_id (str): ID do paciente substituto
        data (str): Data da nova consulta
        horario (str): Horário da nova consulta
    
    Returns:
        dict: Resultado da operação
    """
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Buscar informações da consulta original
        cursor.execute('''
            SELECT * FROM consultas WHERE id = ?
        ''', (consulta_id,))
        
        consulta_original = cursor.fetchone()
        
        if not consulta_original:
            return {'sucesso': False, 'mensagem': 'Consulta não encontrada'}
        
        # Buscar paciente substituto
        cursor.execute('''
            SELECT * FROM pacientes WHERE id = ?
        ''', (paciente_substituto_id,))
        
        paciente = cursor.fetchone()
        
        if not paciente:
            return {'sucesso': False, 'mensagem': 'Paciente não encontrado'}
        
        # Criar nova consulta para o substituto
        cursor.execute('''
            INSERT INTO consultas (
                paciente_id, data, horario, dia_semana, turno,
                procedimento, antecedencia_dias, e_retorno,
                n_remarcacoes, proximo_feriado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            paciente_substituto_id,
            data,
            horario,
            consulta_original['dia_semana'],
            consulta_original['turno'],
            consulta_original['procedimento'],
            0,  # Antecedência imediata
            0,  # Não é retorno
            0,  # Sem remarcações
            consulta_original['proximo_feriado']
        ))
        
        conn.commit()
        conn.close()
        
        return {
            'sucesso': True,
            'mensagem': f'Substituição confirmada! {paciente["nome"]} agendado para {data} às {horario}',
            'nova_consulta_id': cursor.lastrowid
        }
        
    except Exception as e:
        conn.rollback()
        conn.close()
        return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

# Teste
if __name__ == '__main__':
    print("Testando sistema de substituição...\n")
    
    # Simular busca de substitutos para uma consulta
    print("Buscando substitutos para consulta ID 1...")
    
    substitutos = buscar_substitutos(
        consulta_id=1,
        data='2025-04-15',
        horario='14:00',
        n=5
    )
    
    if substitutos:
        print(f"\n{len(substitutos)} substitutos encontrados:\n")
        for i, sub in enumerate(substitutos, 1):
            print(f"{i}. {sub['nome']} ({sub['tipo_pagamento']})")
            print(f"   Probabilidade de falta: {sub['probabilidade_falta']}%")
            print(f"   Score: {sub['score']}/100")
            print(f"   {sub['justificativa']}\n")
    else:
        print("Nenhum substituto encontrado")
