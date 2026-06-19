# OdontoSync

## Introducao

O **OdontoSync** e um sistema inteligente para a gestao de clinicas odontologicas, focado na mitigacao de faltas de pacientes (no-shows) e otimizacao operacional. O setor odontologico sofre rotineiramente com cancelamentos tardios e nao comparecimentos, o que impacta diretamente na receita e na produtividade das clinicas. Para solucionar esse problema, o OdontoSync aplica tecnicas de Machine Learning para prever a probabilidade de falta de cada paciente, permitindo que a administracao da clinica tome acoes preditivas para minimizar horarios ociosos.

Alem do carater preditivo, a plataforma integra funcionalidades de inteligencia artificial generativa e dados climaticos externos para auxiliar a equipe no redirecionamento eficiente de vagas criticas, mantendo a operacao fluida e o fluxo de caixa estavel.

## Arquitetura do Sistema

O projeto foi construído sob uma pilha de tecnologias maduras e direcionadas ao processamento e analise de dados, aliado a uma interface amigavel:

- **Backend:** Python 3.12+ e Flask (padrao Blueprints)
- **Persistencia:** SQLite (banco de dados leve e embarcado)
- **Machine Learning:** Scikit-learn, XGBoost, imbalanced-learn, pandas e numpy
- **Inteligencia Artificial:** API Google Generative AI (Gemini)
- **Visualizacao de Dados:** Matplotlib e Seaborn para graficos de backend
- **Frontend:** Jinja2, HTML5 e Vanilla CSS
- **Integracoes:** OpenWeatherMap (API de dados climaticos)

## Principais Funcionalidades

- **Previsao de Faltas (No-show):** Avaliacao de risco em tempo real (Alto, Medio, Baixo) para cada agendamento com base em dados historicos do paciente, perfil, tipo de procedimento e condicoes climaticas.
- **Gestao Inteligente da Agenda Diaria:** Interface que apresenta a agenda diária com os riscos sinalizados. Permite operacoes interativas para contato e confirmacao automatizada.
- **Reorganizacao e Sugestoes via IA:** Modulo que elenca agendamentos de alto risco e fornece alternativas de reorganizacao (como contatar pacientes de listas de espera), utilizando o modelo Gemini para criar scripts e mensagens de abordagem inteligentes e persuasivas.
- **Simulador de Riscos:** Ferramenta interativa que calcula dinamicamente a probabilidade de falta de um paciente ficticio ou real com base na alteracao manual de variaveis, auxiliando no planejamento de operacoes futuras.
- **Dashboard e Relatorios Visuais:** Area dedicada a analise exploratoria do dataset e entendimento do modelo por meio de graficos estatisticos exportados diretamente do pipeline em Python.
- **Conformidade LGPD (Lei Geral de Protecao de Dados):** Pseudonimizacao na camada de Machine Learning. O sistema trata adequadamente a mascara de dados sensiveis durante a criacao e o uso do modelo analitico.

## Pipeline de Dados e Machine Learning

A arquitetura de Machine Learning esta totalmente integrada, possuindo um pipeline de atualizacao modular:

1. **Extracao e Tratamento:** Executado via `app.ml.gerar_dados`, responsavel por ingerir bases brutas, anonimizar informacoes pessoais e padronizar variaveis.
2. **Treinamento:** Executado via `app.ml.treinar`, roda as etapas de treino de uma floresta de decisao/XGBoost, gerando as matrizes e serializando os artefatos (`.pkl`). Gera automaticamente o relatorio `dados/relatorio_ia_lgpd.md`.
3. **Persistencia Inicial:** Executado via `app.models.popular_banco`, formata as informacoes tratadas para consumo da interface Flask (SQLite).

## Requisitos

- Python 3.12 ou superior
- Docker e Docker Compose (caso prefira instalacao em containers)

## Variaveis de Ambiente

A aplicacao consome diversas variaveis de ambiente fundamentais (`.env`):

- `SECRET_KEY`: Chave de sessao do Flask.
- `DEBUG`: Ativa ou desativa modo de depuracao (True/False).
- `GEMINI_API_KEY`: Token de acesso a API do Google Gemini.
- `USE_AI_SUGGESTIONS`: Habilita (True) ou desabilita (False) a engine de texto com IA.
- `WEATHER_API_KEY`: Chave da API OpenWeatherMap.
- `USE_WEATHER_API`: Habilita integracao de clima real para as inferencias (True/False).

## Execucao em Ambiente Local

Para executar e desenvolver no proprio sistema operacional:

1. Clone o projeto e entre no diretorio correspondente.
2. Crie o ambiente virtual (venv) e ative-o:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux ou macOS
   # venv\Scripts\activate   # Windows
   ```
3. Instale as dependencias requeridas:
   ```bash
   pip install -r requirements.txt
   ```
4. Processe a pipeline do Machine Learning e inicialize o banco de dados:
   ```bash
   python -m app.ml.gerar_dados
   python -m app.ml.treinar
   python -m app.models.popular_banco
   ```
5. Inicie a aplicacao web:
   ```bash
   python run.py
   ```
6. Acesse a interface web em `http://localhost:5000`.

## Execucao via Docker

Para um deploy facilitado e reproduzivel sem a necessidade de configuracao do ambiente local:

1. Faca a construcao da imagem e inicie o container:
   ```bash
   docker compose up --build -d
   ```
2. Para monitorar o estado da execucao e logs:
   ```bash
   docker compose logs -f
   ```
3. Para parar o container:
   ```bash
   docker compose down
   ```

**Configuracoes extras do container (no docker-compose.yml):**
- `BOOTSTRAP_ON_START=True`: Inicia o pipeline de treinamento automaticamente se nao houver dados presentes.
- `BOOTSTRAP_REFRESH_DATA=True`: Forca o treinamento e reposicionamento de todos os dados cada vez que o container subir.

## Estrutura de Diretorios

- `app/`: Core da aplicacao Flask.
  - `ml/`: Scripts de construcao, treinamento e analise da rede preditiva.
  - `models/`: Camada de definicao e interacao com o banco de dados.
  - `routes/`: Controladores da arquitetura MVC.
  - `templates/` e `static/`: Visualizacao e assetos.
- `dados/`: Diretorio de persistencia para o banco SQLite, datasets transformados (`.csv`) e relatorios de auditoria automatica de IA e LGPD.
- `modelo/`: Diretorio destinado aos artefatos serilizados de IA (`random_forest.pkl`, `encoders.pkl`).
