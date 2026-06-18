from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import sys
import os
import base64

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.models.database import get_connection

bp = Blueprint('prontuario', __name__, url_prefix='/prontuario')


def _mascarar_nome(nome):
    partes = [p for p in (nome or '').split() if p]
    if not partes:
        return 'Paciente'
    if len(partes) == 1:
        return f"{partes[0][0]}***"
    return f"{partes[0][0]}*** {partes[-1][0]}***"


@bp.route('/')
def index_prontuario():
    """Tela de seleção de paciente para abrir o prontuário."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id, nome, tipo_pagamento, faixa_etaria, faltas_anteriores, photo_url '
        'FROM pacientes ORDER BY nome ASC'
    )
    pacientes = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return render_template('prontuario_lista.html', pacientes=pacientes, active_page='prontuario')


@bp.route('/<paciente_id>', methods=['GET'])
def visualizar_prontuario(paciente_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nome, faixa_etaria, tipo_pagamento, faltas_anteriores,
               taxa_historica, tempo_como_paciente, fumante,
               doenca_cronica, complexidade_tratamento, photo_url, lgpd_mask
        FROM pacientes
        WHERE id = ?
    ''', (paciente_id,))
    paciente = cursor.fetchone()

    # Buscar consultas do paciente (mais recentes primeiro)
    cursor.execute('''
        SELECT id, data, horario, procedimento, status_atendimento, status_reorganizacao, compareceu
        FROM consultas
        WHERE paciente_id = ?
        ORDER BY data DESC, horario DESC
        LIMIT 20
    ''', (paciente_id,))
    consultas = [dict(r) for r in cursor.fetchall()]

    conn.close()

    if not paciente:
        return render_template('error.html',
                               error_code=404,
                               error_message='Paciente não encontrado',
                               error_description='Não foi possível localizar o prontuário solicitado.'), 404

    paciente_dict = dict(paciente)
    if paciente_dict.get('lgpd_mask', 1) == 1:
        paciente_dict['nome_mascarado'] = _mascarar_nome(paciente_dict.get('nome'))
    else:
        paciente_dict['nome_mascarado'] = paciente_dict.get('nome')

    return render_template('prontuario.html', paciente=paciente_dict, consultas=consultas, active_page='prontuario')


@bp.route('/<paciente_id>', methods=['POST'])
def atualizar_prontuario(paciente_id):
    fumante = int(request.form.get('fumante', 0))
    doenca_cronica = int(request.form.get('doenca_cronica', 0))
    complexidade_tratamento = request.form.get('complexidade_tratamento', 'Baixa')
    if complexidade_tratamento not in ('Baixa', 'Média', 'Alta'):
        complexidade_tratamento = 'Baixa'
        
    nome = request.form.get('nome')
    faixa_etaria = request.form.get('faixa_etaria')
    tipo_pagamento = request.form.get('tipo_pagamento')
    tempo_como_paciente = request.form.get('tempo_como_paciente')

    conn = get_connection()
    cursor = conn.cursor()
    
    # We conditionally update the extra fields to not break anything if they are not provided (e.g. from an old form submit)
    if nome and faixa_etaria and tipo_pagamento and tempo_como_paciente:
        cursor.execute('''
            UPDATE pacientes
            SET fumante = ?,
                doenca_cronica = ?,
                complexidade_tratamento = ?,
                nome = ?,
                faixa_etaria = ?,
                tipo_pagamento = ?,
                tempo_como_paciente = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (fumante, doenca_cronica, complexidade_tratamento, nome, faixa_etaria, tipo_pagamento, int(tempo_como_paciente), paciente_id))
    else:
        cursor.execute('''
            UPDATE pacientes
            SET fumante = ?,
                doenca_cronica = ?,
                complexidade_tratamento = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (fumante, doenca_cronica, complexidade_tratamento, paciente_id))
    conn.commit()
    conn.close()

    flash('Histórico clínico atualizado com sucesso.', 'success')
    return redirect(url_for('prontuario.visualizar_prontuario', paciente_id=paciente_id))


@bp.route('/<paciente_id>/foto', methods=['POST'])
def upload_foto(paciente_id):
    """Salva a foto de perfil do paciente (base64 no banco)."""
    try:
        foto_file = request.files.get('foto')
        if not foto_file:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado.'}), 400

        # Aceitar jpg e png
        allowed = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        if foto_file.content_type not in allowed:
            return jsonify({'sucesso': False, 'mensagem': 'Formato inválido. Use JPG ou PNG.'}), 400

        # Ler e converter para data URI
        foto_bytes = foto_file.read()
        if len(foto_bytes) > 2 * 1024 * 1024:  # 2 MB max
            return jsonify({'sucesso': False, 'mensagem': 'Imagem muito grande (máx 2 MB).'}), 400

        foto_b64 = base64.b64encode(foto_bytes).decode('utf-8')
        data_uri = f"data:{foto_file.content_type};base64,{foto_b64}"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE pacientes SET photo_url = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (data_uri, paciente_id)
        )
        conn.commit()
        conn.close()

        return jsonify({'sucesso': True, 'photo_url': data_uri})
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500


@bp.route('/buscar')
def buscar_pacientes():
    """API para busca de pacientes por nome."""
    q = request.args.get('q', '').strip()
    conn = get_connection()
    cursor = conn.cursor()
    if q:
        cursor.execute(
            'SELECT id, nome, tipo_pagamento, faixa_etaria, faltas_anteriores, photo_url '
            'FROM pacientes WHERE nome LIKE ? ORDER BY nome ASC LIMIT 20',
            (f'%{q}%',)
        )
    else:
        cursor.execute(
            'SELECT id, nome, tipo_pagamento, faixa_etaria, faltas_anteriores, photo_url '
            'FROM pacientes ORDER BY nome ASC LIMIT 20'
        )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({'pacientes': rows})
