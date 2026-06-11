# Relatório de Performance da IA (LGPD)

## 1. Resultado do Treinamento
- **Modelo vencedor:** XGBoost
- **AUC-ROC:** 0.7221
- **Recall (faltas):** 0.7074
- **F1-Score (faltas):** 0.7410
- **Precisão (faltas):** 0.7780

## 2. Comparação entre Modelos
| Modelo | AUC-ROC | Recall | F1-Score |
|---|---:|---:|---:|
| Logistic Regression | 0.7147 | 0.6721 | 0.7206 |
| Random Forest | 0.7098 | 0.7230 | 0.7440 |
| XGBoost | 0.7221 | 0.7074 | 0.7410 |

## 3. Matriz de Confusão
- **TN:** 399
- **FP:** 258
- **FN:** 374
- **TP:** 904

## 4. Principais Variáveis do Modelo
- **n_remarcacoes**: 0.3430
- **faltas_anteriores**: 0.1854
- **proximo_feriado**: 0.0850
- **antecedencia_dias**: 0.0624
- **condicao_clima**: 0.0554

## 5. Variáveis de Usuário Disponíveis (com LGPD)
### Usadas no modelo (minimização de dados)
- faixa_etaria
- tipo_pagamento
- faltas_anteriores
- taxa_historica
- tempo_como_paciente
- fumante
- doenca_cronica
- complexidade_tratamento
- dia_semana
- turno
- procedimento
- antecedencia_dias
- e_retorno
- n_remarcacoes
- proximo_feriado
- condicao_clima
- temperatura

### Mantidas para operação (não usadas no treino)
- paciente_id (pseudônimo)
- nome (mascarado em iniciais)

### Removidas do pipeline de IA por LGPD
- documento
- celular
- prontuário
- nome completo

## 6. Medidas de Conformidade LGPD Aplicadas
1. **Minimização:** treino sem dados pessoais diretos.
2. **Pseudonimização:** ID técnico para cada paciente.
3. **Mascaramento:** nome exibido por iniciais.
4. **Finalidade:** uso dos dados apenas para previsão de faltas e otimização de agenda.

## 7. Observação Metodológica
Para a base importada de pacientes, os desfechos históricos de comparecimento foram construídos para viabilizar o treinamento supervisionado sem usar documentos sensíveis.
