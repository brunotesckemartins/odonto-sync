from flask import Blueprint, render_template, request, redirect, url_for, flash
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from app.models.database import get_connection

bp = Blueprint('prontuario', __name__, url_prefix='/prontuario')


@bp.route('/')
def index_prontuario():
    """Redireciona para o prontuário do primeiro paciente disponível."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM pacientes ORDER BY nome ASC LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    if row:
        return redirect(url_for('prontuario.visualizar_prontuario', paciente_id=row['id']))
    return render_template('error.html',
                           error_code=404,
                           error_message='Nenhum paciente cadastrado',
                           error_description='Não há pacientes no banco de dados ainda.'), 404


def _mascarar_nome(nome):
    partes = [p for p in (nome or '').split() if p]
    if not partes:
        return 'Paciente'
    if len(partes) == 1:
        return f"{partes[0][0]}***"
    return f"{partes[0][0]}*** {partes[-1][0]}***"


@bp.route('/<paciente_id>', methods=['GET'])
def visualizar_prontuario(paciente_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, nome, faixa_etaria, tipo_pagamento, faltas_anteriores,
               taxa_historica, tempo_como_paciente, fumante,
               doenca_cronica, complexidade_tratamento
        FROM pacientes
        WHERE id = ?
    ''', (paciente_id,))
    paciente = cursor.fetchone()
    conn.close()

    if not paciente:
        return render_template('error.html',
                               error_code=404,
                               error_message='Paciente não encontrado',
                               error_description='Não foi possível localizar o prontuário solicitado.'), 404

    paciente_dict = dict(paciente)
    paciente_dict['nome_mascarado'] = _mascarar_nome(paciente_dict.get('nome'))

    return render_template('prontuario.html', paciente=paciente_dict, active_page='prontuario')


@bp.route('/<paciente_id>', methods=['POST'])
def atualizar_prontuario(paciente_id):
    fumante = int(request.form.get('fumante', 0))
    doenca_cronica = int(request.form.get('doenca_cronica', 0))
    complexidade_tratamento = request.form.get('complexidade_tratamento', 'Baixa')
    if complexidade_tratamento not in ('Baixa', 'Média', 'Alta'):
        complexidade_tratamento = 'Baixa'

    conn = get_connection()
    cursor = conn.cursor()
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
