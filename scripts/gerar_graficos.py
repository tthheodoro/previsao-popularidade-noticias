"""
Graph Generator for Report
--------------------------
Generates visualization charts from SQLite database.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import sqlite3
import os

# Database is in the project root's data/ folder
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'portefolio.db')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'output')

def get_connection():
    return sqlite3.connect(DB_PATH)

def gerar_grafico_crescimento():
    """1. Data Volume Evolution"""
    conn = get_connection()
    query = """
    SELECT DATE(Data_Recolha) as Data, COUNT(*) as Total
    FROM Dataset_Social_Real
    GROUP BY DATE(Data_Recolha)
    ORDER BY Data
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("No data for growth chart.")
        return

    df['Acumulado'] = df['Total'].cumsum()

    plt.figure(figsize=(10, 5))
    plt.plot(df['Data'].astype(str), df['Acumulado'], marker='o', color='#6366f1', linewidth=2, markersize=8)
    plt.title('Evolução do Volume de Dados', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Data de Recolha', fontsize=12)
    plt.ylabel('Total de Registos', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_1_crescimento.png'), dpi=300)
    print("Chart 1 saved!")

def gerar_grafico_monitorizacao():
    """2. Monitoring Efficiency (Pie Chart)"""
    conn = get_connection()
    query = """
    SELECT 
        CASE WHEN Avaliado = 1 THEN 'Finalizados (48h)' ELSE 'Em Monitorização' END as Estado,
        COUNT(*) as Total
    FROM Dataset_Social_Real
    GROUP BY Avaliado
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("No data for monitoring chart.")
        return

    plt.figure(figsize=(8, 8))
    cores = ['#6366f1', (1.0, 1.0, 1.0, 0.2)]
    explode = (0.05, 0)
    
    plt.pie(df['Total'], labels=df['Estado'], autopct='%1.1f%%', startangle=140, 
            colors=cores, explode=explode, textprops={'fontsize': 11, 'color': '#fff'})
    plt.title('Eficiência da Monitorização Temporal', fontsize=14, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_2_monitorizacao.png'), dpi=300, facecolor='#0a0f1c')
    print("Chart 2 saved!")

def gerar_grafico_equilibrio():
    """3. Class Balance by Source"""
    conn = get_connection()
    query = """
    SELECT Fonte, Popularidade_Real, COUNT(*) as Total
    FROM Dataset_Social_Real
    WHERE Popularidade_Real IN ('alta', 'média', 'baixa') 
    AND Fonte != 'Update' 
    GROUP BY Fonte, Popularidade_Real
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("No data for balance chart.")
        return

    pivot_df = df.pivot(index='Fonte', columns='Popularidade_Real', values='Total').fillna(0)
    if 'média' in pivot_df.columns:
        pivot_df = pivot_df[['alta', 'média', 'baixa']]

    cores = ['#22c55e', '#f59e0b', '#ef4444']
    ax = pivot_df.plot(kind='bar', figsize=(10, 6), color=cores, width=0.8)
    
    plt.title('Equilíbrio de Classes por Fonte', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Fonte Editorial', fontsize=12)
    plt.ylabel('Quantidade', fontsize=12)
    plt.xticks(rotation=0)
    plt.legend(title='Classe', labels=['Alta', 'Média', 'Baixa'])
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_3_equilibrio.png'), dpi=300)
    print("Chart 3 saved!")

def gerar_grafico_engajamento_real():
    """4. Real Engagement Correlation"""
    conn = get_connection()
    query = """
    SELECT Popularidade_Real, AVG(Likes_48h) as Media_Likes
    FROM Dataset_Social_Real 
    WHERE Avaliado = 1 AND Popularidade_Real IN ('alta', 'média', 'baixa')
    GROUP BY Popularidade_Real
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        print("No data for engagement chart.")
        return

    df['Ordem'] = df['Popularidade_Real'].map({'alta': 1, 'média': 2, 'baixa': 3})
    df = df.sort_values('Ordem')

    plt.figure(figsize=(9, 6))
    cores = ['#22c55e', '#f59e0b', '#ef4444']
    
    barras = plt.bar(df['Popularidade_Real'].str.capitalize(), df['Media_Likes'], color=cores, width=0.6)
    
    plt.title('Engajamento Real ao fim de 48h', fontsize=14, fontweight='bold', pad=15)
    plt.xlabel('Classe Preditiva', fontsize=12)
    plt.ylabel('Média de Likes', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    for barra in barras:
        altura = barra.get_height()
        plt.text(barra.get_x() + barra.get_width()/2., altura + 100,
                 f'{int(altura)}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'grafico_4_engajamento.png'), dpi=300)
    print("Chart 4 saved!")

if __name__ == "__main__":
    print("Generating charts...")
    gerar_grafico_crescimento()
    gerar_grafico_monitorizacao()
    gerar_grafico_equilibrio()
    gerar_grafico_engajamento_real()
    print("All charts generated!")
