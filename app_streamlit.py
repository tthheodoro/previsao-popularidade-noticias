# ============================================================
# APP STREAMLIT - SQL SERVER EDITION
# ============================================================
import streamlit as st
import pandas as pd
import joblib
import os
from datetime import datetime
import db_connection # <--- O NOSSO NOVO MÓDULO

st.set_page_config(page_title="Previsão de Popularidade", layout="wide")
st.title("Previsão de Popularidade (Ligado ao SQL Server)")

# CARREGAR MODELO
path_modelo = "models/modelo_portugues_plus.pkl"
if os.path.exists(path_modelo):
    modelo = joblib.load(path_modelo)
else:
    st.error("⚠️ Modelo não encontrado. Corre o 'main_portugues_plus.py' primeiro.")
    st.stop()

# INPUTS
col1, col2 = st.columns(2)
with col1:
    categoria = st.selectbox("Categoria", ["politica", "economia", "cultura", "desporto", "país", "geral"])
    titulo = st.text_input("Título")
    descricao = st.text_area("Descrição", height=150)
with col2:
    data_pub = st.date_input("Data", datetime.now())
    hora_pub = st.time_input("Hora", datetime.now())

# PREVISÃO
if st.button("🔮 Prever"):
    n_titulo = len(titulo.split()) if titulo else 0
    n_desc = len(descricao.split()) if descricao else 0
    # Sentimento simples (podes importar a função se quiseres)
    pal_pos = ["bom", "excelente", "vitória"]
    pal_neg = ["mau", "crise", "derrota"]
    sent = sum(p in descricao.lower() for p in pal_pos) - sum(p in descricao.lower() for p in pal_neg)
    
    dados = {
        "n_palavras_titulo": n_titulo, "n_palavras_desc": n_desc, "sentimento": sent,
        "dia_semana": data_pub.weekday(), "hora": hora_pub.hour, "categoria": categoria,
        "titulo": titulo, "descricao": descricao # Guardamos isto para o feedback
    }
    
    # Guardar no estado
    st.session_state['dados'] = dados
    st.session_state['pred'] = modelo.predict(pd.DataFrame([dados]))[0]
    st.session_state['feito'] = True

# RESULTADO & FEEDBACK
if st.session_state.get('feito'):
    res = st.session_state['pred']
    st.success(f"Previsão: {res}")
    
    st.write("---")
    st.write("### 🧠 Feedback Humano (Guarda no SQL Server)")
    real = st.radio("Qual a realidade?", ["Baixa", "Média", "Alta"], horizontal=True)
    
    if st.button("✅ Enviar para Base de Dados"):
        try:
            # AQUI ESTÁ A MUDANÇA: Guarda via SQL
            db_connection.salvar_feedback(st.session_state['dados'], real)
            st.success("Feedback guardado no SQL Server com sucesso!")
        except Exception as e:
            st.error(f"Erro ao guardar no SQL: {e}")