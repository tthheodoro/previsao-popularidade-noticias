import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
import joblib
import os

print("🚀 A carregar dados do Facebook...")

# 1. Carregar os dados (O dataset do UCI costuma usar separador ';')
# Ajusta o caminho se o teu CSV estiver noutra pasta
caminho_csv = os.path.join(os.path.dirname(__file__), '..', 'dataset_Facebook.csv')
df = pd.read_csv(caminho_csv, sep=';')

# 2. Selecionar as colunas (Features que sabemos ANTES de publicar)
colunas_input = ['Type', 'Category', 'Post Month', 'Post Weekday', 'Post Hour', 'Paid']
coluna_alvo = 'Total Interactions'

# Limpar linhas que tenham valores vazios nestas colunas
df = df[colunas_input + [coluna_alvo]].dropna()

# 3. Criar as Classes de Popularidade (Alta, Média, Baixa)
q1 = df[coluna_alvo].quantile(0.33)
q2 = df[coluna_alvo].quantile(0.66)

def classificar_popularidade(valor):
    if valor <= q1: return 'baixa'
    elif valor <= q2: return 'média'
    else: return 'alta'

df['popularidade'] = df[coluna_alvo].apply(classificar_popularidade)

X = df[colunas_input]
y = df['popularidade']

# 4. Construir o Pipeline da IA
# O "Type" é texto (Photo, Status), temos de o transformar em números com o OneHotEncoder
preprocessor = ColumnTransformer(
    transformers=[
        ('cat', OneHotEncoder(handle_unknown='ignore'), ['Type'])
    ],
    remainder='passthrough' # Mantém as outras colunas numéricas (Mês, Hora, etc) intactas
)

modelo_social = Pipeline(steps=[
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
])

# 5. Treinar e Guardar o Modelo
print("🧠 A treinar a nova IA para Redes Sociais...")
modelo_social.fit(X, y)

caminho_modelo = os.path.join(os.path.dirname(__file__), 'modelo_social.pkl')
joblib.dump(modelo_social, caminho_modelo)

print(f"✅ SUCESSO! Modelo guardado em: {caminho_modelo}")