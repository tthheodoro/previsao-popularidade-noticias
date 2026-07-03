"""Create SQLite database with all required tables."""
import sqlite3
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'portefolio.db')


def create_database():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS Utilizadores (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Nome TEXT NOT NULL,
        Email TEXT UNIQUE NOT NULL,
        Password_Hash TEXT NOT NULL,
        Data_Criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Noticias (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Titulo TEXT,
        Descricao TEXT,
        Link TEXT UNIQUE,
        DataPublicacao TIMESTAMP,
        Fonte TEXT,
        Categoria TEXT,
        N_Palavras_Titulo INTEGER,
        N_Palavras_Desc INTEGER,
        Dia_Semana INTEGER,
        Hora INTEGER,
        Sentimento INTEGER,
        Popularidade_Real TEXT,
        DataInsercao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Feedback (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Titulo_Input TEXT,
        Descricao_Input TEXT,
        Categoria_Input TEXT,
        N_Palavras_Titulo INTEGER,
        N_Palavras_Desc INTEGER,
        Sentimento INTEGER,
        Dia_Semana INTEGER,
        Hora INTEGER,
        Popularidade_Real TEXT,
        Previsao_IA TEXT,
        Utilizador_ID INTEGER,
        DataFeedback TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (Utilizador_ID) REFERENCES Utilizadores(ID)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Feedback_Social (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Texto_Post TEXT,
        Seguidores INTEGER,
        Likes INTEGER,
        Comentarios INTEGER,
        Mes INTEGER,
        Dia_Semana INTEGER,
        Hora INTEGER,
        N_Hashtags INTEGER,
        N_Palavras INTEGER,
        Popularidade_Real TEXT,
        Previsao_IA TEXT,
        Utilizador_ID INTEGER,
        Data_Registo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (Utilizador_ID) REFERENCES Utilizadores(ID)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS Dataset_Social_Real (
        ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Post_ID_Social TEXT UNIQUE,
        Fonte TEXT,
        Plataforma TEXT,
        Texto_Post TEXT,
        Link_Post TEXT,
        Data_Publicacao TEXT,
        Likes INTEGER DEFAULT 0,
        Comentarios INTEGER DEFAULT 0,
        Partilhas INTEGER DEFAULT 0,
        Popularidade_Real TEXT,
        Data_Recolha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        Avaliado INTEGER DEFAULT 0,
        Link_Imagem TEXT,
        N_Rostos INTEGER DEFAULT 0,
        Brilho_Imagem INTEGER DEFAULT 127,
        Likes_12h INTEGER,
        Likes_24h INTEGER,
        Likes_48h INTEGER
    )''')

    conn.commit()

    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for t in tables:
        print(f"  - {t[0]}")

    conn.close()
    print(f"\nDatabase created at: {DB_PATH}")


if __name__ == "__main__":
    print("Creating database tables...")
    create_database()
