import joblib
import numpy as np
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config

# Cache para modelo e encoders (carregar apenas uma vez)
_modelo = None
_encoders = None

def carregar_modelo():
    """Carrega o modelo e encoders do disco (com cache)"""
    global _modelo, _encoders
    
    if _modelo is None or _encoders is None:
        if not os.path.exists(Config.MODELO_PATH):
            raise FileNotFoundError(
                f"Modelo não encontrado em {Config.MODELO_PATH}. "
                "Execute primeiro: python -m app.ml.treinar"
            )
        
        _modelo = joblib.load(Config.MODELO_PATH)
        _encoders = joblib.load(Config.ENCODERS_PATH)
        print("[OK] Modelo e encoders carregados")
    
    return _modelo, _encoders

def prever_risco(dados_consulta):
    """
    Prediz a probabilidade de falta para uma consulta.
    
    Args:
        dados_consulta (dict): Dicionário com as features da consulta:
            - faixa_etaria: str ('0-17', '18-35', '36-60', '60+')
            - tipo_pagamento: str ('Particular', 'Convênio', 'SUS')
            - faltas_anteriores: int
            - taxa_historica: float (0.0 a 1.0)
            - tempo_como_paciente: int (meses)
            - dia_semana: str ('Monday', 'Tuesday', etc)
            - turno: str ('Manhã', 'Tarde', 'Noite')
            - procedimento: str ('Consulta', 'Limpeza', 'Obturação', etc)
            - antecedencia_dias: int
            - e_retorno: int (0 ou 1)
            - n_remarcacoes: int
            - proximo_feriado: int (0 ou 1)
            - condicao_clima: str ('ensolarado', 'nublado', 'chuvoso', 'tempestade')
            - temperatura: int (graus Celsius)
    
    Returns:
        float: Probabilidade de falta (0.0 a 1.0)
    """
    
    # Carregar modelo
    modelo, encoders = carregar_modelo()
    
    # Preparar features na ordem correta
    features_ordem = [
        'faixa_etaria', 'tipo_pagamento', 'faltas_anteriores', 
        'taxa_historica', 'tempo_como_paciente', 'dia_semana',
        'turno', 'procedimento', 'antecedencia_dias', 'e_retorno',
        'n_remarcacoes', 'proximo_feriado', 'condicao_clima', 'temperatura'
    ]
    
    # Codificar variáveis categóricas
    features_encoded = []
    for feature in features_ordem:
        valor = dados_consulta[feature]
        
        # Aplicar encoding se for categórica
        if feature in encoders:
            try:
                valor = encoders[feature].transform([valor])[0]
            except ValueError:
                # Se o valor não foi visto no treino, usar o mais comum (índice 0)
                print(f"[WARNING] Valor '{valor}' não reconhecido para '{feature}'. Usando padrão.")
                valor = 0
        
        features_encoded.append(valor)
    
    # Converter para array e fazer predição
    X = np.array([features_encoded])
    probabilidade = modelo.predict_proba(X)[0][1]  # Probabilidade da classe 1 (falta)
    
    return float(probabilidade)

def classificar_risco(probabilidade):
    """
    Classifica o risco com base na probabilidade.
    
    Args:
        probabilidade (float): Probabilidade de falta (0.0 a 1.0)
    
    Returns:
        tuple: (categoria, cor_badge)
            - categoria: 'Alto', 'Médio' ou 'Baixo'
            - cor_badge: 'danger', 'warning' ou 'success'
    """
    
    if probabilidade >= Config.RISCO_ALTO:
        return ('Alto', 'danger')
    elif probabilidade >= Config.RISCO_MEDIO:
        return ('Médio', 'warning')
    else:
        return ('Baixo', 'success')

def recomendar_acao(probabilidade, categoria, dados_paciente=None):
    """
    Recomenda ações com base no risco.
    Usa IA se disponível para sugestões mais personalizadas.
    
    Args:
        probabilidade (float): Probabilidade de falta
        categoria (str): Categoria de risco ('Alto', 'Médio', 'Baixo')
        dados_paciente (dict): Dados do paciente para análise personalizada
    
    Returns:
        str: Recomendação de ação
    """
    
    try:
        from app.ml.ai_suggestions import get_ai_assistant
        ai = get_ai_assistant()
        
        if ai.available and dados_paciente:
            return ai.generate_action_recommendation(
                dados_paciente, probabilidade, categoria
            )
    except Exception as e:
        print(f"Erro ao gerar recomendação com IA: {e}")
    
    # Fallback: recomendações padrão sem emojis
    if categoria == 'Alto':
        return (
            "AÇÃO NECESSÁRIA: Confirmar presença com paciente via telefone. "
            "Considerar substituição por paciente da lista de espera."
        )
    elif categoria == 'Médio':
        return (
            "ATENÇÃO: Enviar lembrete via WhatsApp/SMS 24h antes da consulta. "
            "Monitorar confirmação de presença."
        )
    else:
        return (
            "RISCO BAIXO: Enviar lembrete padrão via WhatsApp. "
            "Paciente possui histórico confiável."
        )

def prever_e_classificar(dados_consulta):
    """
    Função completa que prevê e classifica o risco.
    
    Args:
        dados_consulta (dict): Dados da consulta
    
    Returns:
        dict: Resultado com probabilidade, categoria, cor e recomendação
    """
    
    probabilidade = prever_risco(dados_consulta)
    categoria, cor = classificar_risco(probabilidade)
    recomendacao = recomendar_acao(probabilidade, categoria)
    
    return {
        'probabilidade': round(probabilidade * 100, 1),  # Converter para %
        'probabilidade_decimal': probabilidade,
        'categoria': categoria,
        'cor': cor,
        'recomendacao': recomendacao
    }

# Exemplo de uso
if __name__ == '__main__':
    print("[TEST] Testando sistema de inferência...\n")
    
    # Teste 1: Paciente de alto risco
    print("[1] Teste 1: Paciente de ALTO RISCO")
    consulta_alto_risco = {
        'faixa_etaria': '18-35',
        'tipo_pagamento': 'SUS',
        'faltas_anteriores': 3,
        'taxa_historica': 0.6,
        'tempo_como_paciente': 2,
        'dia_semana': 'Monday',
        'turno': 'Noite',
        'procedimento': 'Consulta',
        'antecedencia_dias': 21,
        'e_retorno': 0,
        'n_remarcacoes': 2,
        'proximo_feriado': 1,
        'condicao_clima': 'chuvoso',
        'temperatura': 18
    }
    
    resultado = prever_e_classificar(consulta_alto_risco)
    print(f"   Probabilidade de falta: {resultado['probabilidade']}%")
    print(f"   Categoria: {resultado['categoria']}")
    print(f"   {resultado['recomendacao']}")
    
    # Teste 2: Paciente de baixo risco
    print("\n[2] Teste 2: Paciente de BAIXO RISCO")
    consulta_baixo_risco = {
        'faixa_etaria': '60+',
        'tipo_pagamento': 'Particular',
        'faltas_anteriores': 0,
        'taxa_historica': 0.05,
        'tempo_como_paciente': 36,
        'dia_semana': 'Wednesday',
        'turno': 'Manhã',
        'procedimento': 'Canal',
        'antecedencia_dias': 3,
        'e_retorno': 1,
        'n_remarcacoes': 0,
        'proximo_feriado': 0,
        'condicao_clima': 'ensolarado',
        'temperatura': 25
    }
    
    resultado = prever_e_classificar(consulta_baixo_risco)
    print(f"   Probabilidade de falta: {resultado['probabilidade']}%")
    print(f"   Categoria: {resultado['categoria']}")
    print(f"   {resultado['recomendacao']}")
    
    # Teste 3: Paciente de médio risco
    print("\n[3] Teste 3: Paciente de MÉDIO RISCO")
    consulta_medio_risco = {
        'faixa_etaria': '36-60',
        'tipo_pagamento': 'Convênio',
        'faltas_anteriores': 1,
        'taxa_historica': 0.2,
        'tempo_como_paciente': 12,
        'dia_semana': 'Friday',
        'turno': 'Tarde',
        'procedimento': 'Limpeza',
        'antecedencia_dias': 10,
        'e_retorno': 0,
        'n_remarcacoes': 1,
        'proximo_feriado': 0,
        'condicao_clima': 'nublado',
        'temperatura': 28
    }
    
    resultado = prever_e_classificar(consulta_medio_risco)
    print(f"   Probabilidade de falta: {resultado['probabilidade']}%")
    print(f"   Categoria: {resultado['categoria']}")
    print(f"   {resultado['recomendacao']}")
    
    print("\n[OK] Testes concluídos!")
