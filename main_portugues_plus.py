# ============================================================
# TREINO DO MODELO - SQL SERVER EDITION 🧠
# ============================================================
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import joblib
import os
import warnings
import db_connection # <--- O NOSSO NOVO MÓDULO

warnings.filterwarnings("ignore")

print("🚀 A ligar à Base de Dados SQL Server...")

# 1. CARREGAR DADOS DO SQL (Histórico + Feedback juntos)
try:
    df_noticias, df_feedback = db_connection.carregar_dados_treino()
    print(f"✅ Dados carregados: {len(df_noticias)} notícias históricas | {len(df_feedback)} feedbacks humanos.")
except Exception as e:
    print(f"❌ Erro ao ligar à BD: {e}")
    exit()

# 2. PREPARAR DATASET
# Calcular popularidade para o histórico (baseado em regras)
if not df_noticias.empty:
    q1, q2 = df_noticias["n_palavras_desc"].quantile([0.33, 0.66])
    df_noticias["popularidade"] = pd.cut(
        df_noticias["n_palavras_desc"],
        bins=[-1, q1, q2, 9999],
        labels=["Baixa", "Média", "Alta"]
    )
    
# Preparar Feedback (já tem popularidade real)
if not df_feedback.empty:
    # Mapear colunas do feedback para baterem certo com o treino
    # Nota: No SQL criámos como 'popularidade_real', aqui renomeamos para 'popularidade'
    df_feedback = df_feedback.rename(columns={"popularidade_real": "popularidade"})
    
    # Reforço de aprendizagem (x5)
    df_feedback = pd.concat([df_feedback]*5, ignore_index=True)

# Juntar tudo
cols_treino = ["n_palavras_titulo", "n_palavras_desc", "sentimento", "dia_semana", "hora", "categoria", "popularidade"]

# Garantir que as colunas existem
df_treino = pd.concat([
    df_noticias[cols_treino] if not df_noticias.empty else pd.DataFrame(),
    df_feedback[cols_treino] if not df_feedback.empty else pd.DataFrame()
], ignore_index=True).dropna()

print(f"📊 Dataset Final de Treino: {len(df_treino)} registos.")

# 3. TREINO
features_numericas = ["n_palavras_titulo", "n_palavras_desc", "sentimento", "dia_semana", "hora"]
features_categoricas = ["categoria"]

X = df_treino[features_numericas + features_categoricas]
y = df_treino["popularidade"]

preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), features_numericas),
        ("cat", OneHotEncoder(handle_unknown="ignore"), features_categoricas)
    ]
)

pipeline = Pipeline(steps=[
    ("preprocess", preprocessor),
    ("clf", RandomForestClassifier(n_estimators=300, max_depth=12, random_state=42))
])

pipeline.fit(X, y)

# 4. GUARDAR
os.makedirs("models", exist_ok=True)
joblib.dump(pipeline, "models/modelo_portugues_plus.pkl")
print("✅ Modelo treinado e guardado (SQL Version)!")