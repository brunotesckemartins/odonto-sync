# 🦷 OdontoSync — Sistema de Previsão e Gestão Inteligente de Faltas

> Projeto Integrador de Inteligência Artificial  
> Stack: Python · Flask · SQLite · scikit-learn · XGBoost · HTML/CSS

**Status:** ✅ MVP Completo - v1.1 (com features climáticas)

---

## 🎯 Sobre o Projeto

**OdontoSync** é um sistema inteligente que utiliza Machine Learning para prever faltas em consultas odontológicas, permitindo uma gestão proativa da agenda e redução de ociosidade.

### Funcionalidades Principais

✅ **Agenda Inteligente** - Visualização diária com cálculo de risco em tempo real  
✅ **Simulador de Risco** - Previsão individual manual ou por paciente já cadastrado  
✅ **Reorganização Automática** - Sugestão de substitutos para consultas de alto risco  
✅ **Análise Exploratória** - Gráficos e estatísticas do modelo  
✅ **Interface Minimalista** - Design clean com tema claro/escuro  

---

## 📊 Métricas do Modelo

Modelo: **Logistic Regression** (otimizado com features climáticas)

| Métrica | Valor Alcançado |
|---------|----------------|
| **AUC-ROC** | 0.7192 |
| **Recall** | 0.5704 |
| **F1-Score** | 0.6311 |
| **Acurácia** | 62% |
| **Dataset** | 1200 registros |

### Features Mais Importantes:
1. **Remarcações** (26.4%) - Número de vezes que a consulta foi remarcada
2. **Faltas Anteriores** (19.0%) - Histórico de faltas do paciente
3. **Taxa Histórica** (15.0%) - Taxa de faltas do paciente
4. **Condição Climática** (8.0%) - **NOVA:** Tempo no dia da consulta
5. **Próximo a Feriado** (8.3%) - Se a consulta está próxima a feriados
6. **Tipo de Pagamento** (6.8%) - Particular, Convênio ou SUS
7. **Temperatura** (5.0%) - **NOVA:** Temperatura no dia da consulta
8. **Procedimento** (5.5%) - Tipo de tratamento agendado

### Padrões Identificados:
- Segunda-feira tem **20% mais faltas**
- Particular falta **15% menos**, SUS falta **12% mais**
- Fim do dia (após 17h) aumenta risco em **15%**
- Antecedência > 20 dias aumenta risco em **25%**
- Cada remarcação aumenta risco em **20%**
- **NOVO:** Chuva aumenta faltas em **12%**, tempestade em **20%**
- **NOVO:** Temperaturas extremas (>35°C ou <18°C) aumentam risco em **8%**

---

## 📁 Estrutura do Projeto

```
odontoml/
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   ├── agenda.py         # Rotas da agenda de risco diário
│   │   ├── simulacao.py      # Rota de simulação individual
│   │   ├── reorganizacao.py  # Rota de sugestão de substituição de pacientes
│   │   └── graficos.py       # Rota de análise exploratória
│   ├── models/
│   │   ├── database.py       # Conexão e inicialização do SQLite
│   │   ├── paciente.py       # Model de paciente
│   │   └── consulta.py       # Model de consulta/agendamento
│   ├── ml/
│   │   ├── gerar_dados.py    # Gerador de dataset simulado
│   │   ├── treinar.py        # Pipeline de treinamento do modelo
│   │   ├── inferencia.py     # Função de predição para novas consultas
│   │   └── substituicao.py   # Algoritmo de sugestão de substitutos
│   ├── templates/
│   │   ├── base.html
│   │   ├── agenda.html
│   │   ├── simulacao.html
│   │   ├── reorganizacao.html
│   │   └── graficos.html
│   └── static/
│       ├── css/style.css
│       └── js/main.js
├── modelo/
│   └── random_forest.pkl     # Modelo serializado (gerado no treino)
├── dados/
│   └── agendamentos.csv      # Dataset simulado ou real
├── notebooks/
│   └── exploracao.ipynb      # EDA e experimentos de modelagem
├── requirements.txt
├── config.py
├── run.py
└── README.md
```

---

## 🎯 Escopo do Projeto

### Dentro do escopo
- Agenda diária com pontuação de risco por consulta
- Simulação de risco para consulta individual
- Sugestão de pacientes substitutos com base na probabilidade de falta
- Reorganização inteligente da agenda (acionamento de lista de espera)
- Painel de análise exploratória com gráficos
- Dados simulados com padrões clínicos realistas (com suporte a dados reais futuros)

### Fora do escopo
- Integração com WhatsApp/SMS automatizado
- Integração com softwares externos (Clinicorp, iDental)
- Autenticação de usuários (pode ser adicionada depois)
- Deploy em produção
- Previsão de custo de manutenção

---

## ⚙️ Como Rodar o Projeto

### Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/odontosync.git
cd OdontoSync

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Gere os dados e treine o modelo
python -m app.ml.gerar_dados
python -m app.ml.treinar

# 5. Inicie o servidor
python run.py
```

Acesse: **http://localhost:5000** 🚀

### Rodar com Docker Compose

```bash
# Build e subida do container
docker compose up --build -d

# Acompanhar logs
docker compose logs -f

# Parar ambiente
docker compose down
```

Acesse: **http://localhost:5000**

### Estrutura de Comandos

```bash
# Regenerar dados (800 registros)
python -m app.ml.gerar_dados

# Retreinar modelo
python -m app.ml.treinar

# Popular banco de dados
python -m app.models.popular_banco

# Testar inferência
python -m app.ml.inferencia

# Iniciar servidor de desenvolvimento
python run.py
```

---

## 🎨 Interface

### Design Minimalista
- **Tema Claro/Escuro** - Toggle entre temas com um clique
- **Sidebar Elegante** - Navegação com ícones intuitivos
- **Cards Modernos** - Visualização limpa e organizada
- **Progress Bars** - Indicadores visuais de risco
- **Responsivo** - Funciona em desktop e mobile

### Páginas

1. **📅 Agenda** - Visualização diária com 10 consultas demo
   - Cards de estatísticas (Total, Alto/Médio/Baixo Risco)
   - Tabela com probabilidade e recomendações
   - Progress bars por consulta

2. **🔮 Simulação** - Previsão de risco individual
   - Formulário organizado em seções
   - Resultado com probabilidade destacada
   - Recomendações personalizadas

3. **🔄 Reorganização** - Gestão de alto risco
   - Cards de consultas críticas
   - Busca automática de substitutos
   - Score de compatibilidade

4. **📊 Análise** - Visualizações e métricas
   - 4 gráficos interativos
   - Taxa de falta por dia/turno
   - Importância das features
   - Distribuição do dataset

---

## 🏃 Desenvolvimento por Sprints

O projeto foi desenvolvido em 5 sprints incrementais:

### ✅ Sprint 1 - Fundação (Concluída)
- Estrutura de pastas completa
- Ambiente virtual e dependências
- Gerador de dados com 12 padrões realistas
- Banco SQLite populado com 800 registros

### ✅ Sprint 2 - Machine Learning (Concluída)
- Pipeline de treinamento com 3 modelos
- Sistema de inferência otimizado
- Algoritmo de busca de substitutos
- Métricas: AUC 0.71, Recall 0.67, F1 0.70

### ✅ Sprint 3 - Backend Flask (Concluída)
- 4 blueprints implementados
- 7 rotas funcionais
- Integração com modelo ML
- Dados demo para testes

### ✅ Sprint 4 - Interface (Concluída)
- Design minimalista clean
- Tema claro/escuro funcional
- 5 templates responsivos
- CSS modular com variáveis

### ✅ Sprint 5 - Finalização (Concluída)
- Testes end-to-end aprovados
- Error handlers implementados
- Documentação completa
- Requirements.txt fixado

---

### Sprint 1 — Fundação e Dados Simulados
**Objetivo:** Ter o projeto estruturado, o ambiente funcionando e os dados prontos para modelagem.

**Tarefas:**

- [ ] Criar estrutura de pastas do projeto
- [ ] Criar e ativar o ambiente virtual
- [ ] Criar `requirements.txt` com todas as dependências
- [ ] Criar `config.py` com configurações do Flask e caminhos
- [ ] Criar `run.py` como ponto de entrada da aplicação
- [ ] Criar `app/__init__.py` inicializando o Flask
- [ ] Implementar `app/ml/gerar_dados.py`:
  - Gerar 500 registros simulados com padrões clínicos realistas
  - Padrões embutidos: segunda-feira falta mais, particular falta menos, antecedência longa aumenta risco, fim do dia aumenta risco, remarcações aumentam risco, sazonalidade jan/jul
  - Salvar em `dados/agendamentos.csv`
- [ ] Implementar `app/models/database.py`:
  - Inicializar banco SQLite
  - Criar tabela `pacientes` (id, nome, faixa_etaria, tipo_pagamento, faltas_anteriores, taxa_historica, tempo_como_paciente)
  - Criar tabela `consultas` (id, paciente_id, data, horario, dia_semana, turno, procedimento, antecedencia_dias, e_retorno, n_remarcacoes, proximo_feriado, compareceu)
- [ ] Popular o banco com os dados simulados gerados
- [ ] Testar que o banco está populado corretamente

**Critério de conclusão:** `python -m app.ml.gerar_dados` roda sem erros e gera o CSV. O banco SQLite é criado e populado.

---

### Sprint 2 — Modelo de Machine Learning
**Objetivo:** Ter o pipeline de ML completo: treinamento, avaliação e inferência funcionando.

**Tarefas:**

- [ ] Implementar `app/ml/treinar.py`:
  - Carregar dados do CSV
  - Pré-processar: Label Encoding nas categóricas, separação X/y
  - Balancear classes com upsampling (ou SMOTE se `imbalanced-learn` disponível)
  - Treinar Regressão Logística, Random Forest e XGBoost
  - Avaliar com AUC-ROC, Recall e F1 (classe falta)
  - Salvar o melhor modelo em `modelo/random_forest.pkl`
  - Salvar os encoders em `modelo/encoders.pkl`
- [ ] Implementar `app/ml/inferencia.py`:
  - Carregar modelo e encoders do disco
  - Função `prever_risco(dados_consulta: dict) -> float` que retorna probabilidade de falta (0 a 1)
  - Função `classificar_risco(prob: float) -> tuple` que retorna ('Alto'/'Médio'/'Baixo', 'danger'/'warning'/'success')
- [ ] Implementar `app/ml/substituicao.py`:
  - Função `buscar_substitutos(horario: str, data: str, n=3) -> list`
  - Lógica: buscar pacientes da lista de espera ou com consultas de baixo risco naquele dia
  - Ordenar candidatos por: menor probabilidade de falta + compatibilidade de horário + tipo de procedimento similar
  - Retornar os N melhores substitutos com justificativa
- [ ] Testar inferência com dados de exemplo no terminal
- [ ] Documentar as métricas alcançadas no README

**Critério de conclusão:** `python -m app.ml.treinar` gera o modelo. `inferencia.prever_risco({...})` retorna uma probabilidade correta. AUC-ROC acima de 0.70.

---

### Sprint 3 — Backend Flask (Rotas e Lógica)
**Objetivo:** Ter todas as rotas do Flask implementadas e retornando dados corretos, mesmo sem interface final.

**Tarefas:**

- [ ] Implementar `app/__init__.py` com factory pattern e registro dos blueprints
- [ ] Implementar `app/routes/agenda.py`:
  - Rota `GET /` → buscar consultas do dia no banco, calcular risco de cada uma, ordenar por probabilidade decrescente, passar para template
  - Gerar lista demo de 10 pacientes com dados fictícios se banco estiver vazio
- [ ] Implementar `app/routes/simulacao.py`:
  - Rota `GET /simular` → renderizar formulário
  - Rota `POST /simular` → receber dados do formulário, chamar `prever_risco()`, retornar resultado com badge e ação recomendada
- [ ] Implementar `app/routes/reorganizacao.py`:
  - Rota `GET /reorganizacao` → listar consultas de alto risco do dia com botão "Buscar substituto"
  - Rota `GET /reorganizacao/substitutos/<consulta_id>` → chamar `buscar_substitutos()` e retornar lista de candidatos com probabilidade de falta e justificativa
  - Rota `POST /reorganizacao/confirmar` → confirmar substituição no banco e atualizar agenda
- [ ] Implementar `app/routes/graficos.py`:
  - Rota `GET /graficos` → gerar 4 gráficos matplotlib em base64 e passar para template:
    - Taxa de falta por dia da semana
    - Taxa de falta por turno
    - Importância das features (Random Forest)
    - Distribuição do target (compareceu vs faltou)
- [ ] Testar todas as rotas com `curl` ou no navegador sem CSS

**Critério de conclusão:** Todas as rotas respondem 200. `/` lista pacientes com risco. `/simular` retorna probabilidade. `/reorganizacao/substitutos/1` retorna candidatos.

---

### Sprint 4 — Interface Web (Frontend)
**Objetivo:** Ter a interface visual completa, limpa e funcional em todas as páginas.

**Tarefas:**

- [ ] Criar `app/templates/base.html`:
  - Sidebar com navegação entre as 4 páginas
  - Header e footer consistentes
  - Tema claro, azul e dourado, tipografia Playfair Display + DM Sans
  - Variável `active_page` para destacar item ativo no menu
- [ ] Criar `app/templates/agenda.html`:
  - Cards de estatísticas: total de consultas, alto risco, médio risco
  - Tabela zebrada com: horário, paciente, procedimento, faltas anteriores, antecedência, barra de probabilidade, badge de risco
  - Alerta vermelho se houver pacientes de alto risco
  - Botão "Ver substitutos" em cada linha de alto risco
- [ ] Criar `app/templates/reorganizacao.html`:
  - Listagem de consultas de alto risco
  - Para cada consulta: card com dados da consulta + lista de 3 substitutos sugeridos
  - Cada substituto: nome, probabilidade de falta, justificativa, botão "Confirmar substituição"
  - Confirmação de substituição com feedback visual
- [ ] Criar `app/templates/simulacao.html`:
  - Formulário dividido em seções: "Dados do Paciente" e "Dados da Consulta"
  - Separadores com linha dourada entre seções
  - Caixa de resultado com probabilidade em destaque, badge e ação recomendada
- [ ] Criar `app/templates/graficos.html`:
  - Grid 2x2 com os 4 gráficos em cards
- [ ] Criar `app/static/css/style.css` com variáveis CSS e estilos globais
- [ ] Testar responsividade e navegação entre páginas

**Critério de conclusão:** Todas as páginas carregam com visual correto. Navegação funciona. Substituição de paciente flui do botão até a confirmação.

---

### Sprint 5 — Integração, Testes e Polimento
**Objetivo:** Garantir que tudo funciona integrado, corrigir bugs e deixar o projeto pronto para apresentação.

**Tarefas:**

- [ ] Testar fluxo completo end-to-end:
  - Gerar dados → treinar modelo → abrir agenda → identificar alto risco → buscar substituto → confirmar substituição
- [ ] Testar formulário de simulação com casos extremos (paciente sem histórico, consulta agendada com 1 dia de antecedência)
- [ ] Verificar que o modelo é carregado apenas uma vez (não retreinar a cada request)
- [ ] Adicionar tratamento de erros nas rotas (try/except, mensagens amigáveis)
- [ ] Adicionar mensagem de fallback se modelo não estiver treinado
- [ ] Revisar e atualizar `requirements.txt` com versões fixadas
- [ ] Atualizar este README com:
  - Métricas finais do modelo (AUC, Recall, F1)
  - Print ou GIF das telas principais
  - Instruções de uso atualizadas
- [ ] Preparar demonstração para apresentação:
  - Roteiro de demo: abrir agenda → mostrar alto risco → buscar substituto → confirmar → mostrar gráficos → simular consulta
- [ ] Commit final e tag de versão no GitHub: `v1.0-mvp`

**Critério de conclusão:** Demo roda sem erros do início ao fim. Repositório organizado com commits descritivos por sprint. README atualizado.

---

## 📦 requirements.txt sugerido

```
Flask==3.1.3
pandas==3.0.1
numpy==2.4.3
scikit-learn==1.8.0
xgboost==3.2.0
matplotlib==3.10.8
seaborn==0.13.2
joblib==1.5.3
imbalanced-learn==0.14.1
```

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **Flask 3.1** - Framework web minimalista
- **SQLite** - Banco de dados leve e eficiente
- **Python 3.14** - Linguagem principal

### Machine Learning
- **scikit-learn 1.8** - Modelos e pré-processamento
- **XGBoost 3.2** - Modelo final escolhido
- **SMOTE** - Balanceamento de classes
- **pandas 3.0** - Manipulação de dados

### Visualização
- **matplotlib 3.10** - Gráficos base
- **seaborn 0.13** - Visualizações estatísticas

### Frontend
- **HTML5/CSS3** - Interface minimalista
- **Vanilla JavaScript** - Toggle de tema e interações
- **Design Responsivo** - Mobile-first approach

---

## 📈 Considerações Técnicas

### Dataset Sintético
- **1200 registros** gerados com padrões realistas
- **14 padrões clínicos** embutidos (incluindo clima)
- **Taxa de falta: 56%** (balanceado)
- **Features climáticas:** Condição do tempo e temperatura
- Possibilidade de substituir por dados reais

### Pipeline de ML
1. **Pré-processamento** - Label Encoding para categóricas
2. **Balanceamento** - SMOTE para equilibrar classes
3. **Treinamento** - 3 modelos (Logística, Random Forest, XGBoost)
4. **Seleção** - Melhor modelo por AUC-ROC
5. **Persistência** - Modelo e encoders salvos com joblib

### Performance
- **Cache do modelo** - Carregado uma única vez na memória
- **Inferência rápida** - < 10ms por predição
- **Consultas otimizadas** - Índices no SQLite
- **Gráficos em base64** - Sem necessidade de arquivos estáticos

---

## 🔮 Próximos Passos

### Melhorias Futuras
- [x] Features climáticas preparadas (v1.1)
- [ ] Integração com API de clima em tempo real (OpenWeatherMap)
- [ ] Integração com WhatsApp/SMS para lembretes
- [ ] API REST para integração com sistemas externos
- [ ] Dashboard administrativo completo
- [ ] Autenticação e controle de acesso
- [ ] Histórico de substituições
- [ ] Relatórios em PDF
- [ ] Deploy em produção (Docker + Gunicorn)
- [ ] Testes automatizados (pytest)

### Expansões de ML
- [ ] Modelo de recomendação de horários
- [ ] Previsão de tempo de procedimento
- [ ] Clustering de perfis de pacientes
- [ ] Série temporal para demanda futura

---

## 📝 Notas de Desenvolvimento

### Novidades da Versão 1.1

**Features Climáticas:**
- Adicionadas variáveis `condicao_clima` e `temperatura` ao modelo
- Preparação para integração futura com API de clima
- Configurações prontas para OpenWeatherMap
- Mapeamento de condições climáticas implementado

**Melhorias de Código:**
- Emojis coloridos removidos do código Python
- Mensagens de log profissionais com prefixos [LOAD], [OK], [DATA]
- Ícones HTML/CSS mantidos na interface (melhoram UX)
- Hiperparâmetros otimizados para melhor performance

Veja detalhes completos em: **MELHORIAS_REALIZADAS.md**

### Estrutura do Projeto
```
OdontoSync/
├── app/
│   ├── __init__.py          # Factory do Flask + error handlers
│   ├── routes/              # Blueprints (agenda, simulação, etc)
│   ├── models/              # Database e models SQLite
│   ├── ml/                  # Pipeline ML completo
│   ├── templates/           # Jinja2 templates
│   └── static/              # CSS e JS
├── modelo/                  # Modelos treinados (.pkl)
├── dados/                   # CSV e SQLite database
├── config.py                # Configurações centralizadas
├── run.py                   # Entry point
└── requirements.txt         # Dependências fixadas
```

### Padrões de Código
- **Factory Pattern** para Flask app
- **Blueprints** para organização de rotas
- **Template Inheritance** para HTML
- **CSS Variables** para temas
- **Error Handlers** para UX consistente

---

## 🤖 Notas para uso com Claude Code

- Trabalhe **uma sprint por vez**. Conclua todos os critérios antes de avançar.
- Ao iniciar cada sprint, diga ao Claude: _"Estamos na Sprint X. Implemente as tarefas desta sprint seguindo a estrutura do README."_
- Se uma tarefa gerar erro, resolva antes de passar para a próxima.
- O Claude Code pode rodar `python -m app.ml.treinar` e `python run.py` diretamente para validar cada etapa.
- Mantenha o arquivo `config.py` como fonte única de verdade para caminhos e configurações.

---

## 📊 Estatísticas do Projeto

- **16 arquivos Python** (~4.500 linhas)
- **9 templates HTML**
- **1 arquivo CSS** (~600 linhas)
- **1 arquivo JavaScript**
- **1200 registros** no dataset
- **14 features** no modelo (incluindo clima)
- **7 rotas** implementadas
- **4 gráficos** de análise
- **5 sprints** concluídas
- **34 tarefas** completadas

---

## 👥 Sobre

**OdontoSync** - Sistema de Previsão e Gestão Inteligente de Faltas  
Projeto Integrador de Inteligência Artificial 2026

### Autor
Desenvolvido com ❤️ usando GitHub Copilot CLI

### Licença
Este projeto é livre para uso educacional e não comercial.

---

**Versão:** 1.1.0 (Features Climáticas)  
**Última atualização:** Abril 2026  
**Status:** ✅ Produção (Demo)

---

*Sistema desenvolvido para demonstrar aplicação prática de Machine Learning em gestão de consultórios odontológicos.*
