import pandas as pd
import os
import db_connection  # O teu módulo de ligação

def migrar_csv_para_sql():
    # 1. Encontrar o CSV
    caminho_csv = "noticias_portugal.csv"
    if not os.path.exists(caminho_csv):
        caminho_csv = "data/noticias_portugal.csv"
    
    if not os.path.exists(caminho_csv):
        print("❌ Erro: Não encontro o ficheiro 'noticias_portugal.csv'.")
        return

    print(f"📂 A ler ficheiro: {caminho_csv}...")
    
    # 2. Ler o CSV
    try:
        df = pd.read_csv(caminho_csv)
        print(f"📊 Total de linhas no CSV: {len(df)}")
    except Exception as e:
        print(f"❌ Erro ao abrir CSV: {e}")
        return

    # 3. LIMPEZA PROFUNDA (A Correção do Erro) 🧹
    
    # Converter data
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce")
    
    # Preencher textos vazios com string vazia ou padrão
    df["titulo"] = df["titulo"].fillna("Sem Título")
    df["descricao"] = df["descricao"].fillna("")
    df["fonte"] = df["fonte"].fillna("Desconhecida")
    df["categoria"] = df["categoria"].fillna("geral")
    df["link"] = df["link"].fillna("")

    # Preencher NÚMEROS vazios com 0 e forçar que sejam INTEIROS
    # Isto resolve o erro do "float"
    cols_numericas = ["n_palavras_titulo", "n_palavras_desc", "dia_semana", "hora", "sentimento"]
    for col in cols_numericas:
        if col in df.columns:
            df[col] = df[col].fillna(0).astype(int)
        else:
            df[col] = 0 # Se a coluna não existir, cria com 0

    # Remover linhas que continuem inválidas (sem link ou título)
    df = df.dropna(subset=["titulo", "link"])
    
    # Filtrar apenas linhas onde o link não está vazio
    df = df[df["link"] != ""]

    print(f"✅ Dados limpos. A preparar para enviar {len(df)} notícias...")

    # 4. Enviar para o SQL Server
    print("🚀 A enviar dados para o SQL Server...")
    try:
        db_connection.salvar_noticias_batch(df)
        print("✅ Migração concluída com sucesso!")
    except Exception as e:
        print(f"❌ Ainda deu erro no SQL: {e}")

if __name__ == "__main__":
    migrar_csv_para_sql()