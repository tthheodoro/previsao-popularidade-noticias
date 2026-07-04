"""
Pipeline de MLOps: Treino do Modelo Multimodal para Redes Sociais
-----------------------------------------------------------------
Este script é executado periodicamente para realizar o treino recursivo da IA.
Funde métricas de envolvimento social com características visuais extraídas
por Deep Learning (ResNet18) e aplica o feedback corretivo do utilizador.
"""

import pandas as pd
import numpy as np
import joblib
import os
import requests
from io import BytesIO
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
import json
from datetime import datetime

# Garante que o interpretador encontra o módulo db_connection na pasta app
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))
from db_connection import get_connection


import torch
from torchvision import transforms
from torchvision.models import resnet18, ResNet18_Weights
from PIL import Image

def atualizar_modelo():
    print("Acedendo ao Azure SQL para fundir Dados Reais + Feedback Humano...")

    # 1. CARREGAR DADOS (Histórico Consolidado e Feedback Humano)
    # Nota de Arquitetura: A coluna 'Partilhas' foi descontinuada do dataset
    query_real = """
    SELECT Texto_Post, Link_Imagem, Likes, Comentarios, Partilhas, 
           N_Rostos, Brilho_Imagem, Popularidade_Real as Popularidade 
    FROM Dataset_Social_Real 
    WHERE Avaliado = 1
    """

    # No feedback manual, assumimos valores padrão se não preencheres
    query_feedback = """
    SELECT Texto_Post, '' as Link_Imagem, 0 as Likes, 0 as Comentarios, 0 as Partilhas, 
           0 as N_Rostos, 127 as Brilho_Imagem, Popularidade_Real as Popularidade 
    FROM Feedback_Social
    """

    try:
        with get_connection() as conn:
            df_real = pd.read_sql(query_real, conn)
            df_feed = pd.read_sql(query_feedback, conn)

        # LÓGICA DE NEGÓCIO (Active Learning): Oversampling (x10) do feedback humano
        # Força o modelo a penalizar os erros reportados pelo utilizador mais do que os dados orgânicos.
        if not df_feed.empty:
            df_feed = pd.concat([df_feed] * 10, ignore_index=True)

        df = pd.concat([df_real, df_feed], ignore_index=True).dropna(subset=['Popularidade'])

    except Exception as e:
        print(f"Erro ao ler SQL: {e}")
        return

    if df.empty:
        print("Sem dados (Avaliado=1) para treinar. O robô ainda está a processar os posts?")
        return

    # 2. CONFIGURAÇÃO DE DEEP LEARNING (ResNet18 - Transfer Learning)
    # Instancia a arquitetura pré-treinada removendo a camada de classificação final
    weights = ResNet18_Weights.DEFAULT
    modelo_visao = resnet18(weights=weights)
    extrator = torch.nn.Sequential(*list(modelo_visao.children())[:-1])
    extrator.eval()
    preprocess = weights.transforms()

    def extrair_features(url):
        if not url or str(url) == 'nan' or "http" not in str(url): 
            return np.zeros(512)
        try:
            res = requests.get(url, timeout=5)
            img = Image.open(BytesIO(res.content)).convert('RGB')
            tensor = preprocess(img).unsqueeze(0)
            with torch.no_grad():
                return extrator(tensor).squeeze().numpy()
        except:
            return np.zeros(512)

    print(f"A processar {len(df)} imagens com ResNet18 (Deep Learning)...")
    features_list = df['Link_Imagem'].apply(extrair_features)
    df_img = pd.DataFrame(features_list.to_list(), index=df.index)

    # 3. CONSTRUÇÃO DO VETOR MULTIMODAL E TREINO

    colunas_reais = ['Likes', 'Comentarios', 'Partilhas', 'N_Rostos', 'Brilho_Imagem']
    
    # Fusão: 4 Variáveis Numéricas/Físicas + 512 Variáveis Semânticas Visuais (Total: 516 features)
    X = pd.concat([df[colunas_reais], df_img], axis=1).fillna(0)
    y = df['Popularidade']

    print("A treinar o Random Forest...")
    # n_jobs=-1 permite utilizar todos os núcleos lógicos do processador para acelerar o treino
    modelo = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    modelo.fit(X.values, y)

    # ==========================================
    # 4. AVALIAÇÃO DO MODELO
    # ==========================================
    print("\n📈 A avaliar o modelo...")
    X_train, X_test, y_train, y_test = train_test_split(X.values, y, test_size=0.2, random_state=42)
    y_pred = modelo.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
    conf_matrix = confusion_matrix(y_test, y_pred)

    # Cross-validation
    cv_scores = cross_val_score(modelo, X.values, y, cv=5, scoring='accuracy')
    cv_mean = cv_scores.mean()
    cv_std = cv_scores.std()

    # Save metrics to JSON
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "dataset_size": len(df),
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "cross_val_accuracy_mean": float(cv_mean),
        "cross_val_accuracy_std": float(cv_std),
        "confusion_matrix": conf_matrix.tolist()
    }

    metrics_path = os.path.join(os.path.dirname(__file__), "metricas_social.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"📊 Métricas guardadas em {metrics_path}")

    # Print summary table
    print("\n" + "="*50)
    print("RESUMO DA AVALIAÇÃO - Modelo de Redes Sociais")
    print("="*50)
    print(f"{'Métrica':<30} {'Valor':<20}")
    print("-"*50)
    print(f"{'Tamanho do Dataset':<30} {len(df):<20}")
    print(f"{'Acurácia':<30} {accuracy:.4f}")
    print(f"{'Precisão (weighted)':<30} {precision:.4f}")
    print(f"{'Revocação (weighted)':<30} {recall:.4f}")
    print(f"{'F1-Score (weighted)':<30} {f1:.4f}")
    print(f"{'Cross-Val Acurácia (média)':<30} {cv_mean:.4f}")
    print(f"{'Cross-Val Acurácia (std)':<30} {cv_std:.4f}")
    print("="*50)

    # 5. ATUALIZAR O FICHEIRO .PKL
    caminho_pkl = os.path.join(os.path.dirname(__file__), 'modelo_social.pkl')
    joblib.dump(modelo, caminho_pkl)
    print(f"SUCESSO! Modelo atualizado com {len(df)} exemplos.")

if __name__ == "__main__":
    atualizar_modelo()