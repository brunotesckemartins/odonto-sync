import os
import sys
from datetime import datetime, timedelta

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config
from app.models.database import get_connection
from app.ml.ai_suggestions import get_ai_assistant
from app.ml.inferencia import prever_risco


HORARIOS_PADRAO = ['08:00', '09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00', '18:00']


def _determinar_turno(horario):
    hora = int(horario.split(':')[0])
    if hora < 12:
        return 'Manhã'
    if hora < 18:
        return 'Tarde'
    return 'Noite'


def _dados_predicao(paciente, procedimento, data, horario, antecedencia_dias, n_remarcacoes):
    return {
        'faixa_etaria': paciente['faixa_etaria'],
        'tipo_pagamento': paciente['tipo_pagamento'],
        'faltas_anteriores': paciente['faltas_anteriores'],
        'taxa_historica': paciente['taxa_historica'],
        'tempo_como_paciente': paciente['tempo_como_paciente'],
        'fumante': paciente['fumante'],
        'doenca_cronica': paciente['doenca_cronica'],
        'complexidade_tratamento': paciente['complexidade_tratamento'],
        'dia_semana': datetime.strptime(data, '%Y-%m-%d').strftime('%A'),
        'turno': _determinar_turno(horario),
        'procedimento': procedimento,
        'antecedencia_dias': max(1, int(antecedencia_dias)),
        'e_retorno': 0,
        'n_remarcacoes': max(0, int(n_remarcacoes)),
        'proximo_feriado': 0,
        'condicao_clima': 'ensolarado',
        'temperatura': 25
    }


def _buscar_consulta_e_paciente(consulta_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, p.id AS p_id, p.nome, p.faixa_etaria, p.tipo_pagamento,
               p.faltas_anteriores, p.taxa_historica, p.tempo_como_paciente,
               p.fumante, p.doenca_cronica, p.complexidade_tratamento
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.id = ?
    ''', (consulta_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def _gerar_justificativa(candidato, prob_falta):
    razoes = []
    if prob_falta < 0.3:
        razoes.append('histórico confiável')
    if candidato['faltas_anteriores'] == 0:
        razoes.append('sem faltas anteriores')
    if candidato['tipo_pagamento'] == 'Particular':
        razoes.append('pagamento particular')
    if candidato['tempo_como_paciente'] > 24:
        razoes.append('paciente há mais de 2 anos')
    if candidato['taxa_historica'] < 0.1:
        razoes.append('taxa de falta < 10%')
    if not razoes:
        razoes.append('disponível no horário')
    return 'Recomendado: ' + ', '.join(razoes)


def _calcular_score_compatibilidade(candidato, prob_falta):
    score = 0.0
    score += (1 - prob_falta) * 45
    faltas = min(candidato['faltas_anteriores'], 6)
    score += (6 - faltas) / 6 * 18

    if candidato['tipo_pagamento'] == 'Particular':
        score += 16
    elif candidato['tipo_pagamento'] == 'Convênio':
        score += 12
    else:
        score += 8

    tempo_norm = min(candidato['tempo_como_paciente'], 72) / 72
    score += tempo_norm * 12
    score += (1 - candidato['taxa_historica']) * 9
    return round(score, 2)


def _calcular_confianca_substituto(score, prob_falta, faltas_anteriores):
    confiança = 60
    confiança += (score / 100) * 30
    confiança += (1 - prob_falta) * 10
    confiança -= min(faltas_anteriores, 5) * 2
    return int(min(98, max(40, round(confiança))))


def buscar_substitutos(consulta_id, data, horario, n=3):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento,
               p.faltas_anteriores, p.taxa_historica, p.tempo_como_paciente,
               p.fumante, p.doenca_cronica, p.complexidade_tratamento
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.id = ?
    ''', (consulta_id,))
    consulta_original = cursor.fetchone()
    if not consulta_original:
        conn.close()
        return []

    cursor.execute('''
        SELECT DISTINCT p.*
        FROM pacientes p
        WHERE p.id != ?
          AND p.id NOT IN (
              SELECT paciente_id FROM consultas WHERE data = ? AND horario = ?
          )
        LIMIT 120
    ''', (consulta_original['paciente_id'], data, horario))
    candidatos = cursor.fetchall()
    conn.close()

    if not candidatos:
        return []

    substitutos = []
    for candidato in candidatos:
        dados_consulta = _dados_predicao(
            paciente=candidato,
            procedimento=consulta_original['procedimento'],
            data=data,
            horario=horario,
            antecedencia_dias=1,
            n_remarcacoes=0
        )
        prob_falta = prever_risco(dados_consulta)
        score = _calcular_score_compatibilidade(candidato, prob_falta)
        confianca = _calcular_confianca_substituto(score, prob_falta, candidato['faltas_anteriores'])
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
            'justificativa': _gerar_justificativa(candidato, prob_falta),
            'score': score,
            'confianca': confianca
        })

    substitutos.sort(key=lambda x: x['score'], reverse=True)
    top_substitutos = substitutos[:n]

    ai = get_ai_assistant()
    if ai.available and Config.USE_AI_SUGGESTIONS:
        original_patient = {
            'nome': consulta_original['nome'],
            'probabilidade': 0,
            'faltas_anteriores': consulta_original['faltas_anteriores']
        }
        top_substitutos = ai.analyze_substitutes(original_patient, top_substitutos, data, horario)

    return top_substitutos


def _score_reagendamento(prob_falta_novo, antecedencia_dias, turno, reducao_risco):
    score = (1 - prob_falta_novo) * 68
    if 2 <= antecedencia_dias <= 12:
        score += 12
    elif antecedencia_dias > 20:
        score -= 6
    if turno == 'Manhã':
        score += 9
    elif turno == 'Noite':
        score -= 4
    score += max(0, reducao_risco) * 28
    return round(score, 2)


def sugerir_reagendamento_inteligente(consulta_id, janela_dias=21, max_opcoes=5):
    consulta = _buscar_consulta_e_paciente(consulta_id)
    if not consulta:
        raise ValueError('Consulta não encontrada.')

    hoje = datetime.now()
    data_atual = datetime.strptime(consulta['data'], '%Y-%m-%d')
    dados_origem = _dados_predicao(
        paciente=consulta,
        procedimento=consulta['procedimento'],
        data=consulta['data'],
        horario=consulta['horario'],
        antecedencia_dias=max(1, (data_atual.date() - hoje.date()).days),
        n_remarcacoes=consulta['n_remarcacoes']
    )
    prob_origem = prever_risco(dados_origem)

    conn = get_connection()
    cursor = conn.cursor()
    opcoes = []

    for dia in range(1, janela_dias + 1):
        data_candidata = (hoje + timedelta(days=dia)).strftime('%Y-%m-%d')
        cursor.execute('SELECT horario FROM consultas WHERE data = ?', (data_candidata,))
        ocupados = {row['horario'] for row in cursor.fetchall()}

        for horario in HORARIOS_PADRAO:
            if horario in ocupados:
                continue

            antecedencia = max(1, dia)
            turno = _determinar_turno(horario)
            dados_novos = _dados_predicao(
                paciente=consulta,
                procedimento=consulta['procedimento'],
                data=data_candidata,
                horario=horario,
                antecedencia_dias=antecedencia,
                n_remarcacoes=consulta['n_remarcacoes'] + 1
            )
            prob_novo = prever_risco(dados_novos)
            reducao = prob_origem - prob_novo
            score = _score_reagendamento(prob_novo, antecedencia, turno, reducao)
            confianca = int(min(98, max(40, round((score / 100) * 70 + (1 - prob_novo) * 30))))

            justificativa = (
                f'Risco estimado {round(prob_novo * 100, 1)}% '
                f'(redução de {round(max(0, reducao) * 100, 1)} p.p. vs agenda atual).'
            )
            opcoes.append({
                'data': data_candidata,
                'horario': horario,
                'turno': turno,
                'antecedencia_dias': antecedencia,
                'probabilidade_falta': round(prob_novo * 100, 1),
                'reducao_risco_pp': round(reducao * 100, 1),
                'score': score,
                'confianca': confianca,
                'justificativa': justificativa
            })

    conn.close()
    opcoes_melhora = [op for op in opcoes if op['reducao_risco_pp'] > 0.1]
    if opcoes_melhora:
        opcoes_melhora.sort(key=lambda x: (x['reducao_risco_pp'], x['score']), reverse=True)
        return opcoes_melhora[:max_opcoes]

    # Se não houver melhora de risco, retorna os horários de menor risco absoluto.
    opcoes.sort(key=lambda x: (x['probabilidade_falta'], x['score']))
    return opcoes[:max_opcoes]


def confirmar_substituicao(consulta_id, paciente_substituto_id, data, horario):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM consultas WHERE id = ?', (consulta_id,))
        consulta_original = cursor.fetchone()
        if not consulta_original:
            return {'sucesso': False, 'mensagem': 'Consulta não encontrada'}

        cursor.execute('SELECT * FROM pacientes WHERE id = ?', (paciente_substituto_id,))
        paciente = cursor.fetchone()
        if not paciente:
            return {'sucesso': False, 'mensagem': 'Paciente não encontrado'}

        # Substituição correta: troca o paciente da consulta original (não cria nova consulta no mesmo horário).
        cursor.execute('''
            SELECT COUNT(*) AS total
            FROM consultas
            WHERE paciente_id = ? AND data = ? AND horario = ? AND id != ?
        ''', (paciente_substituto_id, data, horario, consulta_id))
        if cursor.fetchone()['total'] > 0:
            return {'sucesso': False, 'mensagem': 'Paciente substituto já possui consulta neste horário'}

        cursor.execute('''
            UPDATE consultas
            SET paciente_id = ?, status_reorganizacao = 'reorganizada', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (paciente_substituto_id, consulta_id))
        conn.commit()
        return {
            'sucesso': True,
            'mensagem': f'Substituição confirmada! {paciente["nome"]} assumiu a consulta de {data} às {horario}.',
            'consulta_id': consulta_id
        }
    except Exception as e:
        conn.rollback()
        return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}
    finally:
        conn.close()


def confirmar_reagendamento(consulta_id, nova_data, novo_horario):
    if not nova_data or not novo_horario:
        return {'sucesso': False, 'mensagem': 'Data e horário são obrigatórios para reagendamento'}

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM consultas WHERE id = ?', (consulta_id,))
        consulta = cursor.fetchone()
        if not consulta:
            return {'sucesso': False, 'mensagem': 'Consulta não encontrada'}

        cursor.execute('''
            SELECT COUNT(*) AS total FROM consultas
            WHERE data = ? AND horario = ? AND id != ?
        ''', (nova_data, novo_horario, consulta_id))
        if cursor.fetchone()['total'] > 0:
            return {'sucesso': False, 'mensagem': 'Horário já ocupado'}

        hoje = datetime.now().date()
        data_nova = datetime.strptime(nova_data, '%Y-%m-%d').date()
        antecedencia = max(1, (data_nova - hoje).days)

        cursor.execute('''
            UPDATE consultas
            SET data = ?, horario = ?, dia_semana = ?, turno = ?,
                antecedencia_dias = ?, n_remarcacoes = n_remarcacoes + 1,
                status_reorganizacao = 'reorganizada',
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            nova_data,
            novo_horario,
            datetime.strptime(nova_data, '%Y-%m-%d').strftime('%A'),
            _determinar_turno(novo_horario),
            antecedencia,
            consulta_id
        ))

        conn.commit()
        return {
            'sucesso': True,
            'mensagem': f'Reagendamento confirmado para {nova_data} às {novo_horario}.',
            'consulta_id': consulta_id
        }
    except Exception as e:
        conn.rollback()
        return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}
    finally:
        conn.close()
