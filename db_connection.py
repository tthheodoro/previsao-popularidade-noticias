import pymssql  # Trocámos o pyodbc por este
import pandas as pd

# Mantém os teus dados do Azure iguais
SERVER = 'tuas-credenciais.database.windows.net'
DATABASE = 'ProjetoNoticiasDB'
USERNAME = 'teu-user'
PASSWORD = 'tua-password'

def get_connection():
    try:
        # A ligação com pymssql é ligeiramente mais simples
        return pymssql.connect(server=SERVER, user=USERNAME, password=PASSWORD, database=DATABASE)
    except Exception as e:
        print(f"❌ Erro de ligação ao Azure SQL: {e}")
        return None

def salvar_noticias_batch(df):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    
    inseridos = 0
    for _, row in df.iterrows():
        try:
            cursor.execute("""
                INSERT INTO Noticias (Titulo, Descricao, Link, DataPublicacao, Fonte, Categoria, N_Palavras_Titulo, N_Palavras_Desc, Dia_Semana, Hora, Sentimento)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row['titulo'], row['descricao'], row['link'], row['data_publicacao'],
                row['fonte'], row['categoria'], row['n_palavras_titulo'],
                row['n_palavras_desc'], row['dia_semana'], row['hora'], row['sentimento']
            ))
            inseridos += 1
        except pyodbc.IntegrityError:
            continue # Ignora duplicados silenciosamente
        except Exception as e:
            print(f"Erro ao inserir notícia: {e}")
            
    conn.commit()
    conn.close()
    print(f"✅ Azure SQL: {inseridos} novas notícias inseridas.")

def carregar_dados_treino():
    conn = get_connection()
    if not conn: return pd.DataFrame(), pd.DataFrame()
    
    query_noticias = "SELECT * FROM Noticias"
    query_feedback = "SELECT * FROM Feedback"
    
    df_noticias = pd.read_sql(query_noticias, conn)
    df_feedback = pd.read_sql(query_feedback, conn)
    
    conn.close()
    return df_noticias, df_feedback

def salvar_feedback(dados, realidade):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO Feedback (Titulo_Input, Descricao_Input, Categoria_Input, N_Palavras_Titulo, N_Palavras_Desc, Sentimento, Dia_Semana, Hora, Popularidade_Real)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados.get('titulo', ''), dados.get('descricao', ''), dados['categoria'],
        dados['n_palavras_titulo'], dados['n_palavras_desc'], dados['sentimento'],
        dados['dia_semana'], dados['hora'], realidade
    ))
    
    conn.commit()
    conn.close()
    print(f"✅ Azure SQL: Feedback humano ('{realidade}') guardado com sucesso!")