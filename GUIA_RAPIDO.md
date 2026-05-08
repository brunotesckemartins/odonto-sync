# Guia Rápido - OdontoSync v1.1

## 🚀 Início Rápido

### 1. Configuração Inicial

```bash
# Clonar/navegar para o projeto
cd OdontoSync

# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate     # Windows

# Instalar dependências (se necessário)
pip install -r requirements.txt
```

### 2. Gerar Dados e Treinar Modelo

```bash
# Gerar dataset (usa base real com pseudonimização LGPD se disponível)
python -m app.ml.gerar_dados

# Treinar modelo otimizado
python -m app.ml.treinar

# Testar inferência
python -m app.ml.inferencia
```

### 3. Executar Aplicação Web

```bash
# Iniciar servidor Flask
python run.py

# Acessar no navegador
# http://localhost:5000
```

---

## 📋 Comandos Úteis

### Gerar Novos Dados
```bash
python -m app.ml.gerar_dados
```
**Output:** `dados/agendamentos.csv`

### Retreinar Modelo
```bash
python -m app.ml.treinar
```
**Output:** `modelo/random_forest.pkl`, `modelo/encoders.pkl` e `dados/relatorio_ia_lgpd.md`

### Popular Banco de Dados
```bash
python -m app.models.popular_banco
```
**Output:** `dados/odontoml.db` (SQLite)

### Executar Testes Completos
```bash
./TEST_FINAL.sh
```
**Verifica:** Geração → Treinamento → Inferência

---

## 🌟 Novidades da v1.1

### Features Climáticas
O modelo agora considera condições climáticas:

```python
# Exemplo de uso
consulta = {
    'faixa_etaria': '18-35',
    'tipo_pagamento': 'SUS',
    'faltas_anteriores': 2,
    # ... outras features ...
    'condicao_clima': 'chuvoso',  # NOVO
    'temperatura': 18              # NOVO
}

from app.ml.inferencia import prever_e_classificar
resultado = prever_e_classificar(consulta)
# {'probabilidade': 85.2, 'categoria': 'Alto', ...}
```

### Configuração de API de Clima (Futuro)

1. Obtenha API key: https://openweathermap.org/api
2. Configure variável de ambiente:
```bash
export WEATHER_API_KEY="sua_chave_aqui"
```
3. Ative no `config.py`:
```python
USE_WEATHER_API = True
```

---

## 📊 Interpretação de Resultados

### Categorias de Risco

| Probabilidade | Categoria | Ação Recomendada |
|---------------|-----------|------------------|
| ≥ 60% | **Alto** | Confirmar presença + considerar substituto |
| 30-60% | **Médio** | Enviar lembrete 24h antes |
| < 30% | **Baixo** | Lembrete padrão |

### Features Mais Impactantes

1. **Remarcações** - Cada remarcação aumenta ~20% de risco
2. **Faltas Anteriores** - Histórico é crítico
3. **Clima Ruim** - Chuva +12%, tempestade +20%
4. **Segunda-feira** - +20% de faltas
5. **Antecedência Longa** - >20 dias = +25%

---

## 🔧 Ajustes e Configurações

### Alterar Thresholds de Risco

Edite `config.py`:
```python
RISCO_ALTO = 0.6   # ≥ 60% = Alto
RISCO_MEDIO = 0.3  # 30-60% = Médio
```

### Alterar Tamanho do Dataset

Edite `app/ml/gerar_dados.py`:
```python
def gerar_dados_simulados(n_registros=1200):  # Altere aqui
```

### Alterar Hiperparâmetros

Edite `app/ml/treinar.py` na função `treinar_modelos()`.

---

## 🐛 Solução de Problemas

### Erro: "Modelo não encontrado"
```bash
# Execute o treinamento
python -m app.ml.treinar
```

### Erro: "Dataset não encontrado"
```bash
# Gere os dados primeiro
python -m app.ml.gerar_dados
```

### Warnings sobre feature names
**Normal** - Avisos de compatibilidade do scikit-learn, não afetam funcionamento.

### Porta 5000 já em uso
Edite `run.py`:
```python
app.run(debug=True, port=5001)  # Use outra porta
```

---

## 📈 Validação do Sistema

Execute o teste completo:
```bash
./TEST_FINAL.sh
```

Esperado:
```
[1/3] Testando geração de dados...
    [OK] Dados gerados com sucesso
[2/3] Testando treinamento do modelo...
    [OK] Modelo treinado com sucesso
    [>] AUC-ROC: 0.7192
[3/3] Testando inferência...
    [OK] Inferência funcionando
[SUCCESS] Todos os testes passaram!
```

---

## 📚 Documentação Completa

- **README.md** - Visão geral do projeto
- **CHANGELOG.md** - Histórico de versões
- **MELHORIAS_REALIZADAS.md** - Detalhes técnicos das melhorias
- **RESUMO_EXECUTIVO.md** - Resumo gerencial
- **IMPLEMENTACAO_COMPLETA.txt** - Status da implementação

---

## 🆘 Suporte

### Arquivos de Log
Logs são salvos em `/tmp/test_*.log` durante testes.

### Verificar Versões
```bash
python --version  # 3.14+
pip list | grep -E "flask|pandas|scikit|xgboost"
```

### Reinstalar Dependências
```bash
pip install -r requirements.txt --force-reinstall
```

---

## ✅ Checklist de Uso Diário

- [ ] Ativar ambiente virtual
- [ ] Verificar modelo treinado existe (`modelo/random_forest.pkl`)
- [ ] Iniciar servidor (`python run.py`)
- [ ] Acessar http://localhost:5000
- [ ] Usar funcionalidades:
  - Agenda: Ver riscos do dia
  - Simulação: Prever risco individual
  - Reorganização: Buscar substitutos
  - Análise: Visualizar gráficos

---

**Versão:** 1.1.0  
**Última atualização:** Abril 2026  
**Desenvolvido por:** GitHub Copilot CLI

**Pronto para começar!** 🚀
