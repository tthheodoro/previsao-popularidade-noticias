# ============================================================
# TREINO DO MODELO - SQL SERVER EDITION (Com Proxy Editorial)
# ============================================================
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
import joblib
import os
import warnings
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import db_connection # <--- O NOSSO NOVO MÓDULO

warnings.filterwarnings("ignore")

print("🚀 A ligar à Base de Dados SQL Server...")

# 1. CARREGAR DADOS DO SQL (Histórico + Feedback juntos)
try:
    df_noticias, df_feedback = db_connection.carregar_dados_treino()  
    df_noticias.columns = df_noticias.columns.str.lower()
    if not df_feedback.empty:
        df_feedback.columns = df_feedback.columns.str.lower()
    print(f"Colunas detetadas no Histórico: {list(df_noticias.columns)}")
    print(f"✅ Dados carregados: {len(df_noticias)} notícias históricas | {len(df_feedback)} feedbacks humanos.")
except Exception as e:
    print(f"❌ Erro ao ligar à BD: {e}")
    exit()

# ==========================================
# 2. PREPARAR DATASET (A GRANDE MUDANÇA)
# ==========================================

# Preparar o Histórico de Notícias
if not df_noticias.empty:
    # Já não inventamos a popularidade! Usamos a coluna 'popularidade_real' gerada pelo scraper
    if 'popularidade_real' in df_noticias.columns:
        df_noticias = df_noticias.rename(columns={"popularidade_real": "popularidade"})
        # ATENÇÃO: Limpar as notícias velhas (que sacaste ontem) e que não têm esta nova coluna preenchida
        df_noticias = df_noticias.dropna(subset=["popularidade"])
        # Garantir que tudo está em minúsculas (alta, média, baixa)
        df_noticias["popularidade"] = df_noticias["popularidade"].str.lower()
    else:
        print("⚠️ ERRO: A coluna 'popularidade_real' não existe nas notícias. Corre o scraper primeiro!")

# Preparar Feedback Humano (que vale ouro!)
if not df_feedback.empty:
    # Mapear colunas do feedback para baterem certo com o treino
    if 'popularidade_real' in df_feedback.columns:
        df_feedback = df_feedback.rename(columns={"popularidade_real": "popularidade"})
    elif 'realidade' in df_feedback.columns: # Caso a base de dados chame 'realidade'
        df_feedback = df_feedback.rename(columns={"realidade": "popularidade"})
    
    if 'categoria' not in df_feedback.columns:
        df_feedback['categoria'] = 'geral' # Se faltar no SQL, preenchemos com 'geral'

    # Reforço de aprendizagem (Multiplicamos o feedback humano por 5 para o modelo lhe dar mais importância)
    df_feedback = pd.concat([df_feedback]*5, ignore_index=True)

# Juntar os dois mundos (Histórico + Feedback)
cols_treino = ["n_palavras_titulo", "n_palavras_desc", "sentimento", "dia_semana", "hora", "categoria", "popularidade"]

# Garantir que as colunas existem antes de juntar
df_treino = pd.concat([
    df_noticias[cols_treino] if not df_noticias.empty else pd.DataFrame(columns=cols_treino),
    df_feedback[cols_treino] if not df_feedback.empty else pd.DataFrame(columns=cols_treino)
], ignore_index=True).dropna()

print(f"📊 Dataset Final de Treino: {len(df_treino)} registos válidos com popularidade.")

if len(df_treino) == 0:
    print("❌ Não há dados suficientes para treinar. Corre o teu script de extração primeiro!")
    exit()

# ==========================================
# 3. TREINO DA INTELIGÊNCIA ARTIFICIAL
# ==========================================
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

# ==========================================
# 4. GUARDAR O CÉREBRO
# ==========================================
os.makedirs("models", exist_ok=True)
joblib.dump(pipeline, "models/modelo_portugues_plus.pkl")
print("✅ SUCESSO! Novo Modelo treinado com dados reais e guardado (SQL Version)!")