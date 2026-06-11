import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score, recall_score, f1_score, classification_report, confusion_matrix, precision_score
from imblearn.over_sampling import SMOTE
import joblib
import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config import Config

import sqlite3

def carregar_dados_do_pep():
    """Carrega o dataset diretamente do banco de dados (PEP)"""
    print("[LOAD] Extraindo histórico do Prontuário Eletrônico...")
    
    # Caminho do banco (ajuste se a chave DB_PATH for diferente no seu config.py)
    db_path = Config.DATABASE_PATH

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Banco de dados não encontrado: {db_path}")
    
    conn = sqlite3.connect(db_path)
    
    query = """
SELECT 
    p.faixa_etaria, p.tipo_pagamento, p.faltas_anteriores, p.taxa_historica, p.tempo_como_paciente,
    p.fumante, p.doenca_cronica, p.complexidade_tratamento,
    c.dia_semana, c.turno, c.procedimento, c.antecedencia_dias, c.e_retorno, c.n_remarcacoes, 
    c.proximo_feriado, c.condicao_clima, c.temperatura, c.compareceu
FROM consultas c
JOIN pacientes p ON c.paciente_id = p.id
WHERE c.compareceu IS NOT NULL
"""
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) < 100:
        print("   [WARNING] Poucos dados históricos encontrados. O modelo pode sofrer overfitting.")
        
    print(f"   [OK] {len(df)} consultas históricas carregadas do banco")
    return df

def preprocessar_dados(df):
    """Pré-processa os dados: encoding e separação X/y"""
    print("\n[PREP] Pré-processando dados...")
    
    # Colunas para treino (remover identificadores e target)
    colunas_treino = [
        'faixa_etaria', 'tipo_pagamento', 'faltas_anteriores',
        'taxa_historica', 'tempo_como_paciente', 'fumante',
        'doenca_cronica', 'complexidade_tratamento', 'dia_semana',
        'turno', 'procedimento', 'antecedencia_dias', 'e_retorno',
        'n_remarcacoes', 'proximo_feriado', 'condicao_clima', 'temperatura'
    ]
    
    # Separar features e target
    X = df[colunas_treino].copy()
    y = 1 - df['compareceu']  # Inverter: 1 = faltou, 0 = compareceu
    
    print(f"   • Target (faltou): {y.sum()} casos positivos ({y.mean()*100:.1f}%)")
    
    # Label Encoding para variáveis categóricas
    encoders = {}
    colunas_categoricas = ['faixa_etaria', 'tipo_pagamento', 'complexidade_tratamento', 'dia_semana', 'turno', 'procedimento', 'condicao_clima']
    
    for coluna in colunas_categoricas:
        le = LabelEncoder()
        X[coluna] = le.fit_transform(X[coluna])
        encoders[coluna] = le
    
    print(f"   [OK] {len(colunas_categoricas)} variáveis categóricas codificadas")
    
    return X, y, encoders

def balancear_dados(X_train, y_train):
    """Balanceia as classes usando SMOTE"""
    print("\n[SMOTE] Balanceando classes...")
    
    print(f"   Antes: Classe 0={sum(y_train==0)}, Classe 1={sum(y_train==1)}")
    
    try:
        smote = SMOTE(random_state=Config.RANDOM_STATE)
        X_train_balanced, y_train_balanced = smote.fit_resample(X_train, y_train)
        print(f"   Depois: Classe 0={sum(y_train_balanced==0)}, Classe 1={sum(y_train_balanced==1)}")
        print(f"   [OK] SMOTE aplicado com sucesso")
        return X_train_balanced, y_train_balanced
    except Exception as e:
        print(f"   WARNING  SMOTE falhou: {e}")
        print(f"   INFO  Continuando sem balanceamento")
        return X_train, y_train

def treinar_modelos(X_train, y_train, X_test, y_test):
    """Treina múltiplos modelos e retorna o melhor"""
    print("\n[TRAIN] Treinando modelos...")
    
    modelos = {
        'Logistic Regression': LogisticRegression(
            max_iter=2000, 
            random_state=Config.RANDOM_STATE,
            class_weight='balanced',
            C=0.5,
            solver='liblinear'
        ),
        'Random Forest': RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=10,
            min_samples_leaf=4,
            random_state=Config.RANDOM_STATE,
            class_weight='balanced',
            max_features='sqrt'
        ),
        'XGBoost': XGBClassifier(
            n_estimators=250,
            max_depth=5,
            learning_rate=0.02,
            min_child_weight=3,
            subsample=0.9,
            colsample_bytree=0.9,
            gamma=0.15,
            reg_alpha=0.2,
            reg_lambda=1.5,
            random_state=Config.RANDOM_STATE,
            scale_pos_weight=(len(y_train) - sum(y_train)) / sum(y_train) if sum(y_train) > 0 else 1,
            eval_metric='logloss'
        )
    }
    
    resultados = {}
    
    for nome, modelo in modelos.items():
        print(f"\n   [DATA] Treinando {nome}...")
        
        # Treinar
        modelo.fit(X_train, y_train)
        
        # Predições
        y_pred = modelo.predict(X_test)
        y_proba = modelo.predict_proba(X_test)[:, 1]
        
        # Métricas
        auc = roc_auc_score(y_test, y_proba)
        recall = recall_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred)
        
        resultados[nome] = {
            'modelo': modelo,
            'auc': auc,
            'recall': recall,
            'f1': f1,
            'y_pred': y_pred,
            'y_proba': y_proba
        }
        
        print(f"      [>] AUC-ROC: {auc:.4f}")
        print(f"      [>] Recall:  {recall:.4f}")
        print(f"      [>] F1-Score: {f1:.4f}")
    
    # Escolher o melhor modelo (priorizar AUC)
    melhor_nome = max(resultados.keys(), key=lambda k: resultados[k]['auc'])
    melhor = resultados[melhor_nome]
    
    print(f"\n   [BEST] Melhor modelo: {melhor_nome}")
    print(f"      [>] AUC-ROC: {melhor['auc']:.4f}")
    print(f"      [>] Recall:  {melhor['recall']:.4f}")
    print(f"      [>] F1-Score: {melhor['f1']:.4f}")
    
    return melhor['modelo'], melhor_nome, melhor, resultados

def avaliar_modelo(modelo, nome, X_test, y_test, y_pred):
    """Avalia o modelo e imprime relatório detalhado"""
    print(f"\n[EVAL] Avaliação detalhada do {nome}:")
    
    # Classification Report
    report_text = classification_report(y_test, y_pred, target_names=['Compareceu', 'Faltou'])
    report_dict = classification_report(y_test, y_pred, target_names=['Compareceu', 'Faltou'], output_dict=True)
    print("\n" + report_text)
    
    # Confusion Matrix
    cm = confusion_matrix(y_test, y_pred)
    print("\nMatriz de Confusão:")
    print(f"   TN={cm[0,0]:3d}  FP={cm[0,1]:3d}")
    print(f"   FN={cm[1,0]:3d}  TP={cm[1,1]:3d}")
    
    # Feature Importance (se disponível)
    top_features = []
    if hasattr(modelo, 'feature_importances_'):
        print("\n[INFO] Top 5 features mais importantes:")
        importances = modelo.feature_importances_
        feature_names = [
            'faixa_etaria', 'tipo_pagamento', 'faltas_anteriores',
            'taxa_historica', 'tempo_como_paciente', 'fumante',
            'doenca_cronica', 'complexidade_tratamento', 'dia_semana',
            'turno', 'procedimento', 'antecedencia_dias', 'e_retorno',
            'n_remarcacoes', 'proximo_feriado', 'condicao_clima', 'temperatura'
        ]
        
        indices = np.argsort(importances)[::-1][:5]
        for i, idx in enumerate(indices, 1):
            print(f"   {i}. {feature_names[idx]}: {importances[idx]:.4f}")
            top_features.append((feature_names[idx], float(importances[idx])))

    return {
        'report_text': report_text,
        'report_dict': report_dict,
        'confusion_matrix': cm,
        'top_features': top_features
    }

def salvar_modelo(modelo, encoders):
    """Salva o modelo e os encoders no disco"""
    print("\n[SAVE] Salvando modelo e encoders...")
    
    # Garantir que o diretório existe
    os.makedirs(Config.MODELO_DIR, exist_ok=True)
    
    # Salvar modelo
    joblib.dump(modelo, Config.MODELO_PATH)
    print(f"   [OK] Modelo salvo em: {Config.MODELO_PATH}")
    
    # Salvar encoders
    joblib.dump(encoders, Config.ENCODERS_PATH)
    print(f"   [OK] Encoders salvos em: {Config.ENCODERS_PATH}")


def salvar_relatorio_performance(nome_modelo, melhor_resultado, todos_resultados, avaliacao, y_test):
    """Gera relatório em markdown com métricas e recorte LGPD."""
    caminho_relatorio = os.path.join(Config.DADOS_DIR, 'relatorio_ia_lgpd.md')
    cm = avaliacao['confusion_matrix']
    report = avaliacao['report_dict']

    linhas_modelos = []
    for nome, resultado in todos_resultados.items():
        linhas_modelos.append(
            f"| {nome} | {resultado['auc']:.4f} | {resultado['recall']:.4f} | {resultado['f1']:.4f} |"
        )

    top_features_md = '\n'.join(
        [f"- **{nome}**: {valor:.4f}" for nome, valor in avaliacao['top_features']]
    ) or '- Modelo sem feature importance disponível.'

    conteudo = f"""# Relatório de Performance da IA (LGPD)

## 1. Resultado do Treinamento
- **Modelo vencedor:** {nome_modelo}
- **AUC-ROC:** {melhor_resultado['auc']:.4f}
- **Recall (faltas):** {melhor_resultado['recall']:.4f}
- **F1-Score (faltas):** {melhor_resultado['f1']:.4f}
- **Precisão (faltas):** {precision_score(y_test, melhor_resultado['y_pred'], zero_division=0):.4f}

## 2. Comparação entre Modelos
| Modelo | AUC-ROC | Recall | F1-Score |
|---|---:|---:|---:|
{chr(10).join(linhas_modelos)}

## 3. Matriz de Confusão
- **TN:** {cm[0,0]}
- **FP:** {cm[0,1]}
- **FN:** {cm[1,0]}
- **TP:** {cm[1,1]}

## 4. Principais Variáveis do Modelo
{top_features_md}

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
"""
    with open(caminho_relatorio, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    print(f"   [OK] Relatório salvo em: {caminho_relatorio}")

def main():
    """Pipeline completo de treinamento"""
    
    print("="*60)
    print("OdontoML - Pipeline de Treinamento Contínuo")
    print("="*60)
    
    # 1. Carregar dados diretamente do PEP
    df = carregar_dados_do_pep()
    if len(df) < 30:
        print("Dados insuficientes")
        return
    
    # O restante continua igual...
    # 2. Pré-processar
    X, y, encoders = preprocessar_dados(df)
    
    # 3. Dividir treino/teste
    print(f"\n[SPLIT]  Dividindo dados (test_size={Config.TEST_SIZE})...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, 
        test_size=Config.TEST_SIZE, 
        random_state=Config.RANDOM_STATE,
        stratify=y
    )
    print(f"   • Treino: {len(X_train)} registros")
    print(f"   • Teste:  {len(X_test)} registros")
    
    # 4. Balancear
    X_train_balanced, y_train_balanced = balancear_dados(X_train, y_train)
    
    # 5. Treinar modelos
    melhor_modelo, melhor_nome, melhor_resultado, todos_resultados = treinar_modelos(
        X_train_balanced, y_train_balanced, X_test, y_test
    )
    
    # 6. Avaliar em detalhes
    avaliacao = avaliar_modelo(melhor_modelo, melhor_nome, X_test, y_test, melhor_resultado['y_pred'])
    
    # 7. Verificar se atende os critérios
    print("\n" + "="*60)
    print("[DATA] Verificação dos Critérios de Aceitação:")
    print("="*60)
    
    auc_ok = melhor_resultado['auc'] >= 0.75
    recall_ok = melhor_resultado['recall'] >= 0.70
    f1_ok = melhor_resultado['f1'] >= 0.65
    
    print(f"   AUC-ROC > 0.75:  {melhor_resultado['auc']:.4f} {'[OK]' if auc_ok else '[FAIL]'}")
    print(f"   Recall > 0.70:   {melhor_resultado['recall']:.4f} {'[OK]' if recall_ok else '[FAIL]'}")
    print(f"   F1-Score > 0.65: {melhor_resultado['f1']:.4f} {'[OK]' if f1_ok else '[FAIL]'}")
    
    if auc_ok and recall_ok and f1_ok:
        print("\n   [SUCCESS] TODOS OS CRITÉRIOS ATENDIDOS!")
    else:
        print("\n   [WARNING] Alguns critérios não foram atendidos")
        print("       Considere ajustar hiperparâmetros ou gerar mais dados")
    
    # 8. Salvar
    salvar_modelo(melhor_modelo, encoders)
    salvar_relatorio_performance(melhor_nome, melhor_resultado, todos_resultados, avaliacao, y_test)
    
    print("\n" + "="*60)
    print("[OK] Treinamento concluído com sucesso!")
    print("="*60)

if __name__ == '__main__':
    main()
