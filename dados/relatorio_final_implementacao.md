# Relatório Final de Implementação - OdontoSync

## Escopo Executado
1. Remoção de usuários fictícios e migração para base real de pacientes.
2. Adequação LGPD para treino e operação.
3. Retreino da IA com dataset atualizado.
4. Implementação de reagendamento inteligente para consultas de alto risco.
5. Geração de relatório técnico para apresentação.

## 1) Dados reais e remoção de fictícios
- O pipeline `app/ml/gerar_dados.py` foi refeito para ler planilha/CSV real.
- IDs de pacientes são pseudonimizados (`PACR...`) e o nome operacional é mascarado em iniciais.
- Campos sensíveis (documento, celular, prontuário e nome completo) não entram no pipeline de treino.
- FallBacks fictícios foram removidos das telas:
  - `app/routes/agenda.py`
  - `app/routes/reorganizacao.py`

## 2) Conformidade LGPD aplicada
- **Minimização de dados:** modelo treina apenas com variáveis comportamentais e operacionais.
- **Pseudonimização:** identificador técnico para uso interno.
- **Mascaramento:** exibição de nome sem identificação direta.
- **Finalidade:** uso focado em previsão de faltas e otimização de agenda.

## 3) Performance atual da IA
- Modelo vencedor: **XGBoost**
- AUC-ROC: **0.7325**
- Recall (faltas): **0.7175**
- F1-Score (faltas): **0.7523**
- Precisão (faltas): **0.7905**

Relatório completo de métricas e variáveis: `dados/relatorio_ia_lgpd.md`

## 4) Variáveis disponíveis (LGPD)
### Usadas no modelo
- faixa_etaria
- tipo_pagamento
- faltas_anteriores
- taxa_historica
- tempo_como_paciente
- dia_semana
- turno
- procedimento
- antecedencia_dias
- e_retorno
- n_remarcacoes
- proximo_feriado
- condicao_clima
- temperatura

### Mantidas para operação (não entram no treino)
- paciente_id (pseudônimo)
- nome (iniciais mascaradas)

### Bloqueadas do pipeline de IA
- documento
- celular
- prontuário
- nome completo

## 5) Reagendamento inteligente implementado
### Backend
- `app/ml/substituicao.py`
  - `sugerir_reagendamento_inteligente(...)`
  - `confirmar_reagendamento(...)`
- `app/routes/reorganizacao.py`
  - `GET /reorganizacao/reagendamento/<consulta_id>`
  - `POST /reorganizacao/confirmar-reagendamento`

### Frontend
- `app/templates/reorganizacao.html`
- `app/static/js/main.js`

### Funcionamento
- Para cada consulta de alto risco, o sistema avalia janelas futuras.
- Calcula probabilidade estimada de falta por horário.
- Ordena melhores opções de reagendamento (melhora de risco quando disponível).
- Permite confirmação direta do novo horário no sistema.

## 6) Resultado operacional observado
- Dataset atualizado: **9673 consultas** de **2796 pacientes** (IDs pseudonimizados).
- Banco repovoado com os dados atuais.
- Pipeline de geração, treino e inferência executado com sucesso.
