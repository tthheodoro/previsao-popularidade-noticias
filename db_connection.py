import pymssql
import pandas as pd

# CONFIGURAÇÕES DO AZURE
SERVER = 'servidorprevisaonoticias.database.windows.net'
DATABASE = 'ProjetoNoticiasDB'                               
USERNAME = 'previsaoadmin'                        
PASSWORD = '@Adminprevisao' 

def get_connection():
    try:
        # O pymssql liga-se diretamente sem precisar de drivers ODBC no sistema
        return pymssql.connect(server=SERVER, user=USERNAME, password=PASSWORD, database=DATABASE)
    except Exception as e:
        print(f"❌ Erro de ligação ao Azure SQL: {e}")
        return None

def salvar_noticias_batch(df):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO Noticias (Titulo, Descricao, Link, DataPublicacao, Fonte, Categoria, N_Palavras_Titulo, N_Palavras_Desc, Dia_Semana, Hora, Sentimento)
                VALUES (%s, %s, %s, %s, %s, %s, %d, %d, %d, %d, %d)
            """, (
                row['titulo'], row['descricao'], row['link'], row['data_publicacao'],
                row['fonte'], row['categoria'], int(row['n_palavras_titulo']),
                int(row['n_palavras_desc']), int(row['dia_semana']), int(row['hora']), int(row['sentimento'])
            ))
        except: continue
    conn.commit()
    conn.close()

def salvar_feedback(dados, realidade):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Feedback (Titulo_Input, Descricao_Input, Categoria_Input, N_Palavras_Titulo, N_Palavras_Desc, Sentimento, Dia_Semana, Hora, Popularidade_Real)
        VALUES (%s, %s, %s, %d, %d, %d, %d, %d, %s)
    """, (
        dados.get('titulo', ''), dados.get('descricao', ''), dados['categoria'],
        int(dados['n_palavras_titulo']), int(dados['n_palavras_desc']), int(dados['sentimento']),
        int(dados['dia_semana']), int(dados['hora']), realidade
    ))
    conn.commit()
    conn.close()

def carregar_dados_treino():
    conn = get_connection()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    df_noticias = pd.read_sql("SELECT * FROM Noticias", conn)
    df_feedback = pd.read_sql("SELECT * FROM Feedback", conn)
    conn.close()
    return df_noticias, df_feedback