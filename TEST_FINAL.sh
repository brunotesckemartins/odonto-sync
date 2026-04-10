#!/bin/bash
# Script de teste final - OdontoSync v1.1

echo "=========================================="
echo "  OdontoSync v1.1 - Testes Finais"
echo "=========================================="
echo ""

# Ativar ambiente virtual
source venv/bin/activate

echo "[1/3] Testando geração de dados..."
python -m app.ml.gerar_dados > /tmp/test_gerar.log 2>&1
if [ $? -eq 0 ]; then
    echo "    [OK] Dados gerados com sucesso"
    grep "Total:" /tmp/test_gerar.log
else
    echo "    [FAIL] Erro ao gerar dados"
    exit 1
fi

echo ""
echo "[2/3] Testando treinamento do modelo..."
python -m app.ml.treinar > /tmp/test_treinar.log 2>&1
if [ $? -eq 0 ]; then
    echo "    [OK] Modelo treinado com sucesso"
    grep "AUC-ROC" /tmp/test_treinar.log | head -4
else
    echo "    [FAIL] Erro ao treinar modelo"
    exit 1
fi

echo ""
echo "[3/3] Testando inferência..."
python -m app.ml.inferencia > /tmp/test_inferencia.log 2>&1
if [ $? -eq 0 ]; then
    echo "    [OK] Inferência funcionando"
    grep "Probabilidade" /tmp/test_inferencia.log
else
    echo "    [FAIL] Erro na inferência"
    exit 1
fi

echo ""
echo "=========================================="
echo "  [SUCCESS] Todos os testes passaram!"
echo "=========================================="
echo ""
echo "Features implementadas:"
echo "  - Remoção de emojis coloridos"
echo "  - Features climáticas (clima + temperatura)"
echo "  - Modelo otimizado (1200 registros)"
echo "  - Configuração para API de clima"
echo ""
echo "Arquivos gerados:"
ls -lh dados/*.csv modelo/*.pkl | awk '{print "  - " $9 " (" $5 ")"}'
echo ""
echo "Pronto para uso!"
