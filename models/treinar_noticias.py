"""
Pipeline de Treino: Modelo de Website e Notícias
------------------------------------------------
Este script é executado via GitHub Actions para realizar o treino recursivo da IA.
Extrai o histórico de notícias e o feedback humano da Azure SQL Database, 
aplica processamento tabular (StandardScaler/OneHotEncoder) e treina um classificador Random Forest.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import joblib
import os
import warnings
import sys
import json
from datetime import datetime

# Garante que o Python encontra o ficheiro db_connection.py na pasta app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

import db_connection 

warnings.filterwarnings("ignore")

print("🔌 A ligar à Base de Dados SQL Server para treino de Website...")

# 1. CARREGAR DADOS DO SQL (Histórico + Feedback juntos)
try:
    df_noticias, df_feedback = db_connection.carregar_dados_treino()  
    
    # Se a base de dados falhar, o sys.exit(1) força o workflow do GitHub Actions a falhar (log vermelho)
    if df_noticias is None:
        print("🚨 Falha crítica: Não foi possível obter dados da BD.")
        sys.exit(1)

    df_noticias.columns = df_noticias.columns.str.lower()
    
    if not df_feedback.empty:
        df_feedback.columns = df_feedback.columns.str.lower()
        
    print(f"✅ Dados carregados: {len(df_noticias)} notícias históricas | {len(df_feedback)} feedbacks humanos.")

except Exception as e:
    print(f"❌ Erro ao ligar à BD: {e}")
    sys.exit(1)

# ==========================================
# 2. PRÉ-PROCESSAMENTO E ENGENHARIA DE DADOS
# ==========================================


if not df_noticias.empty:
    if 'popularidade_real' in df_noticias.columns:
        df_noticias = df_noticias.rename(columns={"popularidade_real": "popularidade"})
        df_noticias = df_noticias.dropna(subset=["popularidade"])
        df_noticias["popularidade"] = df_noticias["popularidade"].str.lower()
    else:
        print("⚠️ Aviso: A coluna 'popularidade_real' não existe nas notícias.")


if not df_feedback.empty:
    if 'popularidade_real' in df_feedback.columns:
        df_feedback = df_feedback.rename(columns={"popularidade_real": "popularidade"})
    elif 'realidade' in df_feedback.columns: 
        df_feedback = df_feedback.rename(columns={"realidade": "popularidade"})
    
    if 'categoria' not in df_feedback.columns:
        df_feedback['categoria'] = 'geral'

    # Reforço de aprendizagem: Multiplicamos o feedback humano por 5
    # Isto garante que a IA "ouve" mais o que tu corrigiste no site do que os dados automáticos
    df_feedback = pd.concat([df_feedback]*5, ignore_index=True)


cols_treino = ["n_palavras_titulo", "n_palavras_desc", "sentimento", "dia_semana", "hora", "categoria", "popularidade"]

# Fusão final do dataset
df_treino = pd.concat([
    df_noticias[cols_treino] if not df_noticias.empty else pd.DataFrame(columns=cols_treino),
    df_feedback[cols_treino] if not df_feedback.empty else pd.DataFrame(columns=cols_treino)
], ignore_index=True).dropna()

print(f"📊 Dataset Final de Treino: {len(df_treino)} registos válidos.")

if len(df_treino) == 0:
    print("🚨 Não há dados suficientes para treinar!")
    sys.exit(1)

# ==========================================
# 3. CONSTRUÇÃO DO PIPELINE DE MACHINE LEARNING
# ==========================================
features_numericas = ["n_palavras_titulo", "n_palavras_desc", "sentimento", "dia_semana", "hora"]
features_categoricas = ["categoria"]

X = df_treino[features_numericas + features_categoricas]
y = df_treino["popularidade"]

# O ColumnTransformer normaliza os números (StandardScaler) e converte a categoria de texto em colunas binárias (OneHotEncoder)
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), features_numericas),
        ("cat", OneHotEncoder(handle_unknown="ignore"), features_categoricas)
    ]
)

# Encadeamento das transformações com o classificador final
pipeline = Pipeline(steps=[
    ("preprocess", preprocessor),
    ("clf", RandomForestClassifier(n_estimators=300, max_depth=12, random_state=42))
])

print("🧠 A treinar o Random Forest (Website)...")
pipeline.fit(X, y)

# ==========================================
# 4. AVALIAÇÃO DO MODELO
# ==========================================
print("\n📈 A avaliar o modelo...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
y_pred = pipeline.predict(X_test)

accuracy = accuracy_score(y_test, y_pred)
precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
conf_matrix = confusion_matrix(y_test, y_pred)

# Cross-validation
cv_scores = cross_val_score(pipeline, X, y, cv=5, scoring='accuracy')
cv_mean = cv_scores.mean()
cv_std = cv_scores.std()

# Save metrics to JSON
metrics = {
    "timestamp": datetime.now().isoformat(),
    "dataset_size": len(df_treino),
    "accuracy": float(accuracy),
    "precision": float(precision),
    "recall": float(recall),
    "f1": float(f1),
    "cross_val_accuracy_mean": float(cv_mean),
    "cross_val_accuracy_std": float(cv_std),
    "confusion_matrix": conf_matrix.tolist()
}

metrics_path = os.path.join("models", "metricas_noticias.json")
os.makedirs("models", exist_ok=True)
with open(metrics_path, "w") as f:
    json.dump(metrics, f, indent=2)
print(f"📊 Métricas guardadas em {metrics_path}")

# Print summary table
print("\n" + "="*50)
print("RESUMO DA AVALIAÇÃO - Modelo de Notícias")
print("="*50)
print(f"{'Métrica':<30} {'Valor':<20}")
print("-"*50)
print(f"{'Tamanho do Dataset':<30} {len(df_treino):<20}")
print(f"{'Acurácia':<30} {accuracy:.4f}")
print(f"{'Precisão (weighted)':<30} {precision:.4f}")
print(f"{'Revocação (weighted)':<30} {recall:.4f}")
print(f"{'F1-Score (weighted)':<30} {f1:.4f}")
print(f"{'Cross-Val Acurácia (média)':<30} {cv_mean:.4f}")
print(f"{'Cross-Val Acurácia (std)':<30} {cv_std:.4f}")
print("="*50)

# ==========================================
# 5. Criação do modelo .pkl
# ==========================================
caminho_modelo = os.path.join("modelo_noticias.pkl")
joblib.dump(pipeline, caminho_modelo)

print(f"\n✅ SUCESSO! Modelo de Notícias guardado em {caminho_modelo}")