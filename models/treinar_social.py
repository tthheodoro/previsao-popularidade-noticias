import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
import joblib
import os

print("🚀 A preparar os dados do Facebook com as novas variáveis científicas...")
caminho_csv = 'dataset_Facebook.csv'
df = pd.read_csv(caminho_csv, sep=';')

colunas_base = ['Type', 'Category', 'Post Month', 'Post Weekday', 'Post Hour', 'Paid']
coluna_alvo = 'Total Interactions'
df = df[colunas_base + [coluna_alvo]].dropna()

# ==========================================
# 🧪 ENGENHARIA DE DADOS SINTÉTICOS (Para o MVP)
# Baseado em: SEISMIC (2015) e Kalyanam (2016)
# ==========================================
np.random.seed(42)

# 1. Seguidores (Segundo o SEISMIC, interações altas vêm de contas com mais seguidores)
df['Seguidores'] = df[coluna_alvo] * np.random.randint(50, 200, size=len(df)) + np.random.randint(1000, 5000, size=len(df))

# 2. Hashtags (Segundo Kalyanam, eventos muito virais focam-se no tópico e usam MENOS hashtags dispersas)
# Quem tem popularidade acima da média ganha entre 0 a 2 hashtags. Abaixo da média ganha 3 a 10.
mediana_interacoes = df[coluna_alvo].median()
df['N_Hashtags'] = df[coluna_alvo].apply(lambda x: np.random.randint(0, 3) if x > mediana_interacoes else np.random.randint(3, 11))

# 3. Tamanho do texto
df['N_Palavras'] = np.random.randint(10, 150, size=len(df))

# ==========================================

colunas_input = colunas_base + ['Seguidores', 'N_Hashtags', 'N_Palavras']

q1 = df[coluna_alvo].quantile(0.33)
q2 = df[coluna_alvo].quantile(0.66)

def classificar_popularidade(valor):
    if valor <= q1: return 'baixa'
    elif valor <= q2: return 'média'
    else: return 'alta'

df['popularidade'] = df[coluna_alvo].apply(classificar_popularidade)

X = df[colunas_input]
y = df['popularidade']

preprocessor = ColumnTransformer(
    transformers=[('cat', OneHotEncoder(handle_unknown='ignore'), ['Type'])],
    remainder='passthrough'
)

modelo_social = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
])

modelo_social.fit(X, y)
caminho_modelo = os.path.join(os.path.dirname(__file__), 'modelo_social.pkl')
joblib.dump(modelo_social, caminho_modelo)
print("✅ SUCESSO! O Modelo Social avançado foi treinado e guardado!")