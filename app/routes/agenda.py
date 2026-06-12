from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta
import sys
import os
import subprocess
import random

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.models.database import (
    get_consultas_do_dia, get_data_referencia_consultas,
    get_consulta_por_id, get_connection, get_datas_com_consultas
)
import hashlib
from app.ml.inferencia import prever_e_classificar

bp = Blueprint('agenda', __name__)


def _calcular_risco_consultas(consultas):
    """Recebe lista de sqlite3.Row ou dict, retorna lista de dicts enriquecidos com risco."""
    consultas_com_risco = []
    stats = {'total': 0, 'alto_risco': 0, 'medio_risco': 0, 'baixo_risco': 0}

    for consulta in consultas:
        try:
            consulta_dict = dict(consulta)
            dados_consulta = {
                'faixa_etaria': consulta_dict.get('faixa_etaria', '36-60'),
                'tipo_pagamento': consulta_dict.get('tipo_pagamento', 'Convênio'),
                'faltas_anteriores': consulta_dict.get('faltas_anteriores', 0),
                'taxa_historica': consulta_dict.get('taxa_historica', 0.0),
                'tempo_como_paciente': consulta_dict.get('tempo_como_paciente', 12),
                'fumante': consulta_dict.get('fumante', 0),
                'doenca_cronica': consulta_dict.get('doenca_cronica', 0),
                'complexidade_tratamento': consulta_dict.get('complexidade_tratamento', 'Baixa'),
                'dia_semana': consulta_dict.get('dia_semana', 'Wednesday'),
                'turno': consulta_dict.get('turno', 'Tarde'),
                'procedimento': consulta_dict.get('procedimento', 'Consulta'),
                'antecedencia_dias': consulta_dict.get('antecedencia_dias', 7),
                'e_retorno': consulta_dict.get('e_retorno', 0),
                'n_remarcacoes': consulta_dict.get('n_remarcacoes', 0),
                'proximo_feriado': consulta_dict.get('proximo_feriado', 0),
                'condicao_clima': consulta_dict.get('condicao_clima', 'ensolarado'),
                'temperatura': consulta_dict.get('temperatura', 25)
            }
            risco = prever_e_classificar(dados_consulta)
            consulta_dict['risco'] = risco
            consultas_com_risco.append(consulta_dict)
            stats['total'] += 1
            if risco['categoria'] == 'Alto':
                stats['alto_risco'] += 1
            elif risco['categoria'] == 'Médio':
                stats['medio_risco'] += 1
            else:
                stats['baixo_risco'] += 1
        except Exception as e:
            print(f"Erro ao calcular risco: {e}")
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

    consultas_com_risco.sort(key=lambda x: x['risco']['probabilidade'], reverse=True)
    return consultas_com_risco, stats


@bp.route('/')
def index():
    """Página principal: agenda do dia com risco calculado por consulta."""
    hoje = datetime.now().strftime('%Y-%m-%d')
    # Suporte a ?data=YYYY-MM-DD para ver agendas futuras
    data_param = request.args.get('data', '').strip()
    if data_param:
        data_referencia = data_param
    else:
        data_referencia = hoje

    consultas = get_consultas_do_dia(data_referencia)

    if not consultas and not data_param:
        data_disponivel = get_data_referencia_consultas(hoje)
        if data_disponivel:
            data_referencia = data_disponivel
            consultas = get_consultas_do_dia(data_referencia)

    # Datas com consultas (futuras e hoje)
    datas_disponiveis = get_datas_com_consultas(hoje)

    if not consultas:
        return render_template(
            'agenda.html',
            consultas=[],
            stats={'total': 0, 'alto_risco': 0, 'medio_risco': 0, 'baixo_risco': 0},
            data=data_referencia,
            data_selecionada=data_referencia,
            hoje=hoje,
            datas_disponiveis=datas_disponiveis,
            active_page='agenda'
        )

    consultas_com_risco, stats = _calcular_risco_consultas(consultas)

    return render_template(
        'agenda.html',
        consultas=consultas_com_risco,
        stats=stats,
        data=data_referencia,
        data_selecionada=data_referencia,
        hoje=hoje,
        datas_disponiveis=datas_disponiveis,
        active_page='agenda'
    )


@bp.route('/agendamentos-futuros')
def agendamentos_futuros():
    """Exibe todos os agendamentos futuros (a partir de hoje)."""
    hoje = datetime.now().strftime('%Y-%m-%d')

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, p.nome, p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores,
               p.taxa_historica, p.tempo_como_paciente,
               p.fumante, p.doenca_cronica, p.complexidade_tratamento, p.photo_url
        FROM consultas c
        JOIN pacientes p ON c.paciente_id = p.id
        WHERE c.data >= ? AND (c.status_reorganizacao IS NULL OR c.status_reorganizacao != 'reorganizada')
        ORDER BY c.data ASC, c.horario ASC
    ''', (hoje,))
    todas_consultas = cursor.fetchall()
    conn.close()

    consultas_com_risco, stats = _calcular_risco_consultas(todas_consultas) if todas_consultas else ([], {'total': 0, 'alto_risco': 0, 'medio_risco': 0, 'baixo_risco': 0})

    # Agrupar por data para exibição
    from collections import OrderedDict
    consultas_por_data = OrderedDict()
    for c in consultas_com_risco:
        d = c['data']
        if d not in consultas_por_data:
            consultas_por_data[d] = []
        consultas_por_data[d].append(c)

    datas_disponiveis = get_datas_com_consultas(hoje)

    return render_template(
        'agendamentos_futuros.html',
        consultas_por_data=consultas_por_data,
        stats=stats,
        hoje=hoje,
        datas_disponiveis=datas_disponiveis,
        active_page='agenda'
    )


@bp.route('/agendar', methods=['POST'])
def agendar_consulta():
    """Cria uma nova consulta para um paciente existente."""
    try:
        paciente_id = request.form.get('paciente_id', '').strip()
        data_consulta = request.form.get('data', '').strip()
        horario = request.form.get('horario', '').strip()
        procedimento = request.form.get('procedimento', 'Consulta').strip()
        e_retorno = int(request.form.get('e_retorno', 0))

        if not paciente_id or not data_consulta or not horario:
            return jsonify({'sucesso': False, 'mensagem': 'Campos obrigatórios ausentes.'}), 400

        conn = get_connection()
        cursor = conn.cursor()

        # Buscar dados do paciente
        cursor.execute('SELECT * FROM pacientes WHERE id = ?', (paciente_id,))
        paciente = cursor.fetchone()
        if not paciente:
            conn.close()
            return jsonify({'sucesso': False, 'mensagem': 'Paciente não encontrado.'}), 404

        # Calcular campos derivados
        dt = datetime.strptime(data_consulta, '%Y-%m-%d')
        dia_semana = dt.strftime('%A')
        hora_int = int(horario.split(':')[0])
        turno = 'Manhã' if hora_int < 12 else ('Tarde' if hora_int < 18 else 'Noite')
        hoje_dt = datetime.now().date()
        antecedencia = (dt.date() - hoje_dt).days
        antecedencia = max(1, antecedencia)

        # Feriados fixos simples
        feriados_mm_dd = {'01-01','04-21','05-01','09-07','10-12','11-02','11-15','12-25'}
        proximo_feriado = 1 if dt.strftime('%m-%d') in feriados_mm_dd else 0

        cursor.execute('''
            INSERT INTO consultas
                (paciente_id, data, horario, dia_semana, turno, procedimento,
                 antecedencia_dias, e_retorno, n_remarcacoes, proximo_feriado,
                 condicao_clima, temperatura, status_reorganizacao)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 'ensolarado', 25, 'pendente')
        ''', (paciente_id, data_consulta, horario, dia_semana, turno,
              procedimento, antecedencia, e_retorno, proximo_feriado))
        conn.commit()
        nova_id = cursor.lastrowid
        conn.close()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Consulta agendada com sucesso para {data_consulta} às {horario}.',
            'consulta_id': nova_id
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao agendar: {str(e)}'}), 500


@bp.route('/criar-paciente', methods=['POST'])
def criar_paciente():
    """Cria um novo paciente para testes."""
    try:
        nome = request.form.get('nome', '').strip()
        faixa_etaria = request.form.get('faixa_etaria', '36-60').strip()
        tipo_pagamento = request.form.get('tipo_pagamento', 'Particular').strip()
        faltas = int(request.form.get('faltas_anteriores', 0))
        fumante = int(request.form.get('fumante', 0))
        doenca_cronica = int(request.form.get('doenca_cronica', 0))
        complexidade = request.form.get('complexidade_tratamento', 'Baixa').strip()

        if not nome:
            return jsonify({'sucesso': False, 'mensagem': 'Nome é obrigatório.'}), 400

        # Gerar ID único
        import uuid
        paciente_id = str(uuid.uuid4())[:8].upper()

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO pacientes
                (id, nome, faixa_etaria, tipo_pagamento, faltas_anteriores,
                 taxa_historica, tempo_como_paciente, fumante, doenca_cronica, complexidade_tratamento)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (paciente_id, nome, faixa_etaria, tipo_pagamento, faltas,
              round(faltas / max(faltas + 5, 1), 2), random.randint(1, 36),
              fumante, doenca_cronica, complexidade))
        conn.commit()
        conn.close()

        return jsonify({
            'sucesso': True,
            'mensagem': f'Paciente "{nome}" criado com sucesso!',
            'paciente_id': paciente_id,
            'paciente': {
                'id': paciente_id,
                'nome': nome,
                'tipo_pagamento': tipo_pagamento
            }
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao criar paciente: {str(e)}'}), 500


@bp.route('/excluir-paciente/<paciente_id>', methods=['POST'])
def excluir_paciente(paciente_id):
    """Exclui um paciente e todas as suas consultas do banco."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verificar se o paciente existe
        cursor.execute('SELECT id, nome FROM pacientes WHERE id = ?', (paciente_id,))
        paciente = cursor.fetchone()
        if not paciente:
            conn.close()
            return jsonify({'sucesso': False, 'mensagem': 'Paciente não encontrado.'}), 404

        nome = paciente['nome']

        # Excluir consultas e paciente
        cursor.execute('DELETE FROM consultas WHERE paciente_id = ?', (paciente_id,))
        cursor.execute('DELETE FROM pacientes WHERE id = ?', (paciente_id,))
        conn.commit()
        conn.close()

        return jsonify({'sucesso': True, 'mensagem': f'Paciente "{nome}" excluído com sucesso.'})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao excluir paciente: {str(e)}'}), 500


@bp.route('/excluir-consulta/<int:consulta_id>', methods=['POST'])
def excluir_consulta(consulta_id):
    """Exclui uma consulta individual do banco."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT id FROM consultas WHERE id = ?', (consulta_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'sucesso': False, 'mensagem': 'Consulta não encontrada.'}), 404

        cursor.execute('DELETE FROM consultas WHERE id = ?', (consulta_id,))
        conn.commit()
        conn.close()

        return jsonify({'sucesso': True, 'mensagem': 'Consulta excluída com sucesso.'})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao excluir consulta: {str(e)}'}), 500


@bp.route('/limpar-pacientes-demo', methods=['POST'])
def limpar_pacientes_demo():
    """Remove todos os pacientes demo (gerados automaticamente) e suas consultas."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Pacientes demo: aqueles cujas TODAS as consultas são 'ficticio',
        # ou pacientes sem nenhuma consulta real (não ficticia)
        # Estratégia: remover consultas fictícias e depois pacientes sem nenhuma consulta
        cursor.execute("DELETE FROM consultas WHERE status_reorganizacao = 'ficticio'")
        ficticio_count = cursor.rowcount

        # Remover pacientes que ficaram sem nenhuma consulta e cujo ID parece gerado (8 chars uppercase)
        # Para segurança, só remove pacientes sem consultas
        cursor.execute('''
            DELETE FROM pacientes
            WHERE id NOT IN (SELECT DISTINCT paciente_id FROM consultas)
        ''')
        pacientes_count = cursor.rowcount

        conn.commit()
        conn.close()

        return jsonify({
            'sucesso': True,
            'mensagem': f'{ficticio_count} consulta(s) demo removidas. {pacientes_count} paciente(s) sem consultas removidos.'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro: {str(e)}'}), 500


@bp.route('/gerar-agenda-ficticia', methods=['POST'])
def gerar_agenda_ficticia():
    """Gera consultas fictícias para uma data específica para fins de demonstração."""
    try:
        # Suporta data via JSON ou form
        data_alvo = None
        if request.is_json:
            data_alvo = (request.json or {}).get('data', '').strip()
        else:
            data_alvo = request.form.get('data', '').strip()

        if data_alvo:
            # Validar formato
            try:
                dt_alvo = datetime.strptime(data_alvo, '%Y-%m-%d')
            except ValueError:
                return jsonify({'sucesso': False, 'mensagem': 'Data inválida.'}), 400
        else:
            dt_alvo = datetime.now()
            data_alvo = dt_alvo.strftime('%Y-%m-%d')

        dia_semana = dt_alvo.strftime('%A')

        conn = get_connection()
        cursor = conn.cursor()

        # Remover consultas fictícias anteriores desta data
        cursor.execute(
            "DELETE FROM consultas WHERE data = ? AND status_reorganizacao = 'ficticio'",
            (data_alvo,)
        )

        # Buscar pacientes reais
        cursor.execute('SELECT id FROM pacientes ORDER BY RANDOM() LIMIT 14')
        pacientes_ids = [r[0] for r in cursor.fetchall()]

        if not pacientes_ids:
            conn.close()
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum paciente cadastrado.'}), 400

        horarios = [
            '08:00', '08:30', '09:00', '09:30', '10:00', '10:30',
            '11:00', '11:30', '14:00', '14:30', '15:00', '15:30',
            '16:00', '16:30'
        ]
        procedimentos = ['Consulta', 'Limpeza', 'Obturação', 'Extração', 'Canal', 'Clareamento']
        climas = ['ensolarado', 'nublado', 'chuvoso']
        clima_hoje = random.choice(climas)
        temp_hoje = random.randint(20, 32)

        feriados_mm_dd = {'01-01','04-21','05-01','09-07','10-12','11-02','11-15','12-25'}
        proximo_feriado = 1 if dt_alvo.strftime('%m-%d') in feriados_mm_dd else 0

        inseridos = 0
        for i, pid in enumerate(pacientes_ids[:len(horarios)]):
            horario = horarios[i]
            hora_int = int(horario.split(':')[0])
            turno = 'Manhã' if hora_int < 12 else 'Tarde'
            proc = random.choice(procedimentos)
            antecedencia = random.randint(1, 21)
            e_retorno = random.randint(0, 1)
            n_rem = random.choices([0, 1, 2], weights=[0.7, 0.2, 0.1])[0]

            cursor.execute('''
                INSERT INTO consultas
                    (paciente_id, data, horario, dia_semana, turno, procedimento,
                     antecedencia_dias, e_retorno, n_remarcacoes, proximo_feriado,
                     condicao_clima, temperatura, status_reorganizacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ficticio')
            ''', (pid, data_alvo, horario, dia_semana, turno, proc,
                  antecedencia, e_retorno, n_rem, proximo_feriado,
                  clima_hoje, temp_hoje))
            inseridos += 1

        conn.commit()
        conn.close()

        return jsonify({
            'sucesso': True,
            'mensagem': f'{inseridos} consultas demo geradas para {data_alvo}.',
            'redirect': f'/?data={data_alvo}'
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro: {str(e)}'}), 500


@bp.route('/pacientes-lista')
def pacientes_lista():
    """Retorna lista de pacientes para o select do modal de agendamento."""
    try:
        q = request.args.get('q', '').strip()
        conn = get_connection()
        cursor = conn.cursor()
        if q:
            cursor.execute(
                'SELECT id, nome, tipo_pagamento FROM pacientes WHERE nome LIKE ? ORDER BY nome ASC LIMIT 20',
                (f'%{q}%',)
            )
        else:
            cursor.execute('SELECT id, nome, tipo_pagamento FROM pacientes ORDER BY nome ASC LIMIT 300')
        rows = cursor.fetchall()
        conn.close()
        return jsonify({
            'sucesso': True,
            'pacientes': [{'id': r['id'], 'nome': r['nome'], 'tipo_pagamento': r['tipo_pagamento']} for r in rows]
        })
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@bp.route('/contato/<int:consulta_id>')
def contato_agenda(consulta_id):
    """Retorna contato mascarado do paciente da consulta."""
    try:
        consulta = get_consulta_por_id(consulta_id)
        if not consulta:
            return {'sucesso': False, 'mensagem': 'Consulta não encontrada'}, 404

        digest = hashlib.sha256(str(consulta['paciente_id']).encode('utf-8')).hexdigest()
        ddd = int(digest[:2], 16) % 90 + 10
        final = int(digest[-4:], 16) % 10000
        telefone_mascarado = f'({ddd}) 9****-{final:04d}'
        return {
            'sucesso': True,
            'paciente': {'id': consulta['paciente_id'], 'nome': consulta['nome']},
            'telefone_mascarado': telefone_mascarado,
        }
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro ao buscar contato: {str(e)}'}, 500


@bp.route('/registrar-desfecho', methods=['POST'])
def registrar_desfecho_agenda():
    """Registra o desfecho da consulta e fecha ciclo de feedback do modelo."""
    try:
        consulta_id = int(request.form.get('consulta_id'))
        desfecho = request.form.get('desfecho', '').strip()
        if desfecho not in ('Realizado', 'Falta'):
            return {'sucesso': False, 'mensagem': 'Desfecho inválido. Use Realizado ou Falta.'}, 400

        compareceu = 1 if desfecho == 'Realizado' else 0

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, paciente_id FROM consultas WHERE id = ?', (consulta_id,))
        consulta = cursor.fetchone()
        if not consulta:
            conn.close()
            return {'sucesso': False, 'mensagem': 'Consulta não encontrada'}, 404

        cursor.execute('''
            UPDATE consultas
            SET status_atendimento = ?, compareceu = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (desfecho, compareceu, consulta_id))

        if desfecho == 'Falta':
            cursor.execute('''
                UPDATE pacientes
                SET faltas_anteriores = faltas_anteriores + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (consulta['paciente_id'],))

        conn.commit()
        conn.close()
        return {'sucesso': True, 'mensagem': 'Desfecho registrado com sucesso.'}
    except Exception as e:
        return {'sucesso': False, 'mensagem': f'Erro ao registrar desfecho: {str(e)}'}, 500


@bp.route('/admin/retreinar-modelo', methods=['POST'])
def retreinar_modelo_admin():
    """Dispara retreinamento assíncrono do modelo de risco."""
    try:
        subprocess.Popen([sys.executable, "-m", "app.ml.treinar"])
        return jsonify({'sucesso': True, 'mensagem': 'Retreinamento iniciado em segundo plano.'})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': f'Erro ao iniciar retreinamento: {str(e)}'}), 500
