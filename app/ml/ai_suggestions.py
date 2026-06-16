"""
Módulo de sugestões inteligentes usando Google Gemini AI.
Fornece análises contextuais e recomendações personalizadas.
"""

import os
import json
from typing import Dict, List, Optional
from config import Config

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


class AIAssistant:
    """Assistente IA para sugestões inteligentes de reagendamento."""
    
    def __init__(self):
        self.available = False
        self.model = None
        
        if GEMINI_AVAILABLE and Config.GEMINI_API_KEY:
            try:
                genai.configure(api_key=Config.GEMINI_API_KEY)
                self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
                self.available = True
            except Exception as e:
                print(f"Erro ao inicializar Gemini: {e}")
                self.available = False
    
    def analyze_substitutes(self, original_patient: Dict, candidates: List[Dict], 
                          date: str, time: str) -> List[Dict]:
        """
        Analisa candidatos substitutos e gera justificativas inteligentes.
        
        Args:
            original_patient: Dados do paciente original
            candidates: Lista de candidatos com scores
            date: Data da consulta
            time: Horário da consulta
            
        Returns:
            Lista de candidatos com justificativas aprimoradas
        """
        if not self.available or not Config.USE_AI_SUGGESTIONS:
            return self._fallback_analysis(candidates)
        
        enhanced_candidates = []
        
        for candidate in candidates:
            try:
                justification = self._generate_smart_justification(
                    original_patient, candidate, date, time
                )
                candidate['justificativa'] = justification
                enhanced_candidates.append(candidate)
            except Exception as e:
                print(f"Erro na análise IA para candidato {candidate.get('id')}: {e}")
                candidate['justificativa'] = self._simple_justification(candidate)
                enhanced_candidates.append(candidate)
        
        return enhanced_candidates
    
    def _generate_smart_justification(self, original: Dict, candidate: Dict, 
                                     date: str, time: str) -> str:
        """Gera justificativa contextual usando IA."""
        
        prompt = f"""Você é um assistente médico especializado em otimização de agenda odontológica.

CONTEXTO:
- Paciente original com alto risco de falta precisa ser substituído
- Data/Horário: {date} às {time}

DADOS DO PACIENTE ORIGINAL (PEP):
- Nome: {original.get('nome', 'N/A')}
- Probabilidade de falta: {original.get('probabilidade', 0):.1%}
- Faltas anteriores: {original.get('faltas_anteriores', 0)}
- Condições PEP: Fumante ({'Sim' if original.get('fumante') else 'Não'}), Doença Crônica ({'Sim' if original.get('doenca_cronica') else 'Não'})
- Complexidade do Tratamento (PEP): {original.get('complexidade_tratamento', 'Baixa')}

CANDIDATO SUBSTITUTO (PEP):
- Nome: {candidate.get('nome', 'N/A')}
- Probabilidade de falta: {candidate.get('probabilidade', 0):.1%}
- Faltas anteriores: {candidate.get('faltas_anteriores', 0)}
- Idade/Faixa (PEP): {candidate.get('faixa_etaria', 'N/A')}
- Condições PEP: Fumante ({'Sim' if candidate.get('fumante') else 'Não'}), Doença Crônica ({'Sim' if candidate.get('doenca_cronica') else 'Não'})
- Complexidade do Tratamento (PEP): {candidate.get('complexidade_tratamento', 'Baixa')}
- Tipo de pagamento: {candidate.get('tipo_pagamento', 'N/A')}
- Tempo como paciente: {candidate.get('tempo_como_paciente', 0)} meses
- Taxa histórica de faltas: {candidate.get('taxa_historica', 0):.1%}
- Score de compatibilidade algorítmica: {candidate.get('compatibilidade', 0):.0f}/100

TAREFA:
Gere uma justificativa CONCISA (máximo 2 linhas) explicando POR QUE este candidato é uma boa substituição.
Foque em dados objetivos e concretos. Seja direto e profissional.
NÃO use emojis. NÃO use formatação markdown.
Comece com "Indicado:" ou "Recomendado:".

Justificativa:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.3,
                    'max_output_tokens': 150,
                }
            )
            
            justification = response.text.strip()
            
            # Limpar possíveis emojis que a IA possa ter gerado
            justification = self._remove_emojis(justification)
            
            # Garantir que não é muito longo
            if len(justification) > 200:
                justification = justification[:197] + "..."
            
            return justification
            
        except Exception as e:
            print(f"Erro ao gerar justificativa com IA: {e}")
            return self._simple_justification(candidate)
    
    def generate_action_recommendation(self, patient: Dict, probability: float, 
                                      category: str) -> str:
        """Gera recomendação de ação personalizada."""
        
        if not self.available or not Config.USE_AI_SUGGESTIONS:
            return self._fallback_recommendation(category)
        
        prompt = f"""Você é um assistente médico para gestão de agenda odontológica.

DADOS DO PACIENTE:
- Probabilidade de falta: {probability:.1%}
- Categoria de risco: {category}
- Faltas anteriores: {patient.get('faltas_anteriores', 0)}
- Tipo de pagamento: {patient.get('tipo_pagamento', 'N/A')}
- Tempo como paciente: {patient.get('tempo_como_paciente', 0)} meses

TAREFA:
Gere uma recomendação de ação CLARA e OBJETIVA (1-2 linhas) para a equipe de atendimento.
Seja específico e prático. NÃO use emojis. NÃO use formatação markdown.
Foque em ações concretas que podem ser tomadas.

Recomendação:"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.4,
                    'max_output_tokens': 120,
                }
            )
            
            recommendation = response.text.strip()
            recommendation = self._remove_emojis(recommendation)
            
            if len(recommendation) > 180:
                recommendation = recommendation[:177] + "..."
            
            return recommendation
            
        except Exception as e:
            print(f"Erro ao gerar recomendação: {e}")
            return self._fallback_recommendation(category)
    
    @staticmethod
    def _remove_emojis(text: str) -> str:
        """Remove emojis de um texto."""
        import re
        # Remove todos os caracteres emoji usando regex Unicode
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags
            u"\U00002702-\U000027B0"  # dingbats
            u"\U000024C2-\U0001F251"
            u"\U0001F900-\U0001F9FF"  # supplemental symbols
            u"\U00002500-\U00002BEF"  # various symbols
            "]+", flags=re.UNICODE)
        
        text = emoji_pattern.sub(r'', text)
        
        # Remove também símbolos específicos que podem escapar
        symbols_to_remove = ['', '', '', '', '', '', '', '', '']
        for symbol in symbols_to_remove:
            text = text.replace(symbol, '')
        
        return text.strip()
    
    @staticmethod
    def _simple_justification(candidate: Dict) -> str:
        """Gera justificativa simples baseada em regras."""
        reasons = []
        
        prob = candidate.get('probabilidade', 1.0)
        faltas = candidate.get('faltas_anteriores', 0)
        pagamento = candidate.get('tipo_pagamento', '')
        tempo = candidate.get('tempo_como_paciente', 0)
        taxa = candidate.get('taxa_historica', 1.0)
        
        if prob < 0.25:
            reasons.append("probabilidade de falta muito baixa")
        elif prob < 0.35:
            reasons.append("baixa probabilidade de falta")
        
        if faltas == 0:
            reasons.append("histórico sem faltas")
        elif faltas <= 1:
            reasons.append("apenas 1 falta anterior")
        
        if pagamento == 'Particular':
            reasons.append("pagamento particular")
        
        if tempo > 24:
            reasons.append(f"paciente há {tempo} meses")
        
        if taxa < 0.05:
            reasons.append("taxa histórica excelente")
        
        if not reasons:
            reasons.append("perfil adequado para substituição")
        
        return "Indicado: " + ", ".join(reasons[:3]) + "."
    
    @staticmethod
    def _fallback_analysis(candidates: List[Dict]) -> List[Dict]:
        """Análise sem IA, usando regras simples."""
        for candidate in candidates:
            candidate['justificativa'] = AIAssistant._simple_justification(candidate)
        return candidates
    
    @staticmethod
    def _fallback_recommendation(category: str) -> str:
        """Recomendação sem IA, baseada em categoria."""
        recommendations = {
            'Alto': (
                "Ação necessária: Confirmar presença com paciente via telefone. "
                "Considerar substituição por paciente da lista de espera."
            ),
            'Médio': (
                "Atenção: Enviar lembrete via WhatsApp/SMS 24h antes. "
                "Monitorar confirmação de presença."
            ),
            'Baixo': (
                "Risco baixo: Enviar lembrete padrão via WhatsApp. "
                "Paciente possui histórico confiável."
            )
        }
        return recommendations.get(category, "Monitorar agendamento.")


# Instância global
_ai_assistant = None

def get_ai_assistant() -> AIAssistant:
    """Retorna instância singleton do assistente IA."""
    global _ai_assistant
    if _ai_assistant is None:
        _ai_assistant = AIAssistant()
    return _ai_assistant
