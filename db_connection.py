import pyodbc
import pandas as pd

# CONFIGURAÇÃO (O teu servidor!)
SERVER = r'.\SQLEXPRESS' 
DATABASE = 'ProjetoNoticias'

def get_connection():
    """Cria a conexão ao SQL Server"""
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

def carregar_dados_treino():
    """Lê TUDO (Histórico + Feedback) para treinar a IA"""
    conn = get_connection()
    
    # Ler histórico
    df_noticias = pd.read_sql("SELECT * FROM Noticias", conn)
    # Ler feedback
    df_feedback = pd.read_sql("SELECT * FROM Feedback", conn)
    
    conn.close()
    
    # Normalizar nomes das colunas para minúsculas (para o modelo não se baralhar)
    df_noticias.columns = df_noticias.columns.str.lower()
    df_feedback.columns = df_feedback.columns.str.lower()
    
    return df_noticias, df_feedback

def salvar_noticias_batch(df_novas):
    """Guarda várias notícias de uma vez (Scraper)"""
    if df_novas.empty: return
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Query inteligente: Só insere se o Link não existir (evita duplicados)
    query = """
    IF NOT EXISTS (SELECT 1 FROM Noticias WHERE Link = ?)
    BEGIN
        INSERT INTO Noticias (Titulo, Descricao, Link, DataPublicacao, Fonte, Categoria, 
                              N_Palavras_Titulo, N_Palavras_Desc, Dia_Semana, Hora, Sentimento)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    END
    """
    
    count = 0
    for index, row in df_novas.iterrows():
        try:
            params = (
                row['link'], 
                row['titulo'], row['descricao'], row['link'], row['data_publicacao'],
                row['fonte'], row['categoria'], row['n_palavras_titulo'],
                row['n_palavras_desc'], row['dia_semana'], row['hora'], row['sentimento']
            )
            cursor.execute(query, params)
            if cursor.rowcount > 0: count += 1
        except Exception as e:
            print(f"Erro ao inserir: {e}")

    conn.commit()
    conn.close()
    print(f"✅ SQL Server: {count} notícias novas guardadas.")

def salvar_feedback(dados, popularidade):
    """Guarda o feedback manual"""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = """
    INSERT INTO Feedback (Titulo_Input, Descricao_Input, Categoria_Input, 
                          N_Palavras_Titulo, N_Palavras_Desc, Sentimento, 
                          Dia_Semana, Hora, Popularidade_Real)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    params = (
        dados.get('titulo', ''), dados.get('descricao', ''), dados['categoria'],
        dados['n_palavras_titulo'], dados['n_palavras_desc'], dados['sentimento'],
        dados['dia_semana'], dados['hora'], popularidade
    )
    
    cursor.execute(query, params)
    conn.commit()
    conn.close()
    return True