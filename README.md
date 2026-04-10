# OdontoSync

Aplicação web em Flask para previsão de faltas em consultas odontológicas, com apoio à operação da agenda.

## Objetivo

O sistema estima a probabilidade de ausência por consulta e organiza ações operacionais a partir do risco calculado:

- priorização de atendimentos com maior risco;
- simulação de risco por paciente/consulta;
- sugestão de substitutos para vagas críticas;
- visualização de indicadores e gráficos do dataset/modelo.

## Arquitetura

- **Backend:** Flask (blueprints em `app/routes`)
- **Persistência:** SQLite (`dados/odontoml.db`)
- **ML:** scikit-learn + XGBoost (`app/ml`)
- **Visualização:** templates Jinja + Matplotlib/Seaborn

Blueprints principais:

- `/` → agenda diária com classificação de risco;
- `/simular` → formulário e cálculo de risco individual;
- `/reorganizacao` → consultas de alto risco e substituição;
- `/graficos` → análise exploratória do dataset.

## Pipeline de dados e modelo

1. `python -m app.ml.gerar_dados` gera `dados/agendamentos.csv`.
2. `python -m app.ml.treinar` treina e salva:
   - `modelo/random_forest.pkl`
   - `modelo/encoders.pkl`
3. `python -m app.models.popular_banco` popula `dados/odontoml.db`.
4. `python run.py` inicia a aplicação web.

## Requisitos

- Python 3.12+ (recomendado)
- Dependências em `requirements.txt`

## Execução local

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt

python -m app.ml.gerar_dados
python -m app.ml.treinar
python -m app.models.popular_banco
python run.py
```

Aplicação disponível em `http://localhost:5000`.

## Execução com Docker

```bash
docker compose up --build -d
docker compose logs -f
```

## Configuração

Variáveis de ambiente relevantes:

- `SECRET_KEY`
- `DEBUG`
- `GEMINI_API_KEY`
- `USE_AI_SUGGESTIONS`
- `WEATHER_API_KEY`
- `USE_WEATHER_API`

Configuração central: `config.py`.
