"""Tests for app.db_connection — database functions with in-memory SQLite."""

import sqlite3
import pytest
from unittest.mock import patch

# In-memory DB path for testing
IN_MEMORY_DB = ":memory:"

SCHEMA = """
CREATE TABLE Utilizadores (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,
    Email TEXT UNIQUE NOT NULL,
    Password_Hash TEXT NOT NULL,
    Data_Criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Noticias (
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
);

CREATE TABLE Feedback (
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
);

CREATE TABLE Feedback_Social (
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
);

CREATE TABLE Dataset_Social_Real (
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
);
"""


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database and monkeypatch DB_PATH."""
    from app import db_connection

    # Save originals
    original_db_path = db_connection.DB_PATH

    # Monkeypatch DB_PATH to point to in-memory DB
    # We need to patch the module-level DB_PATH used by get_connection()
    with patch.object(db_connection, "DB_PATH", ":memory:"):
        # Get a connection to create tables, then let the module use its own connection
        conn = sqlite3.connect(":memory:", timeout=10)
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.close()

        yield

    # Restore original
    db_connection.DB_PATH = original_db_path


class TestCreateAndGetUser:
    def test_create_user_and_get_by_email(self, in_memory_db):
        from app import db_connection

        # Need to patch get_connection to share the same in-memory DB
        # Since in-memory DBs are connection-specific, we need a different approach
        # Let's use a temp file instead for reliable sharing
        pass

    def test_create_user_and_get_by_email_file(self, tmp_path):
        from app import db_connection
        import tempfile
        import os

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            db_connection.create_user("João", "joao@test.com", "hashed_password_123")

            user = db_connection.get_user_by_email("joao@test.com")
            assert user is not None
            assert user["Nome"] == "João"
            assert user["ID"] is not None
            assert user["Password_Hash"] == "hashed_password_123"

    def test_get_user_by_email_nonexistent(self, tmp_path):
        from app import db_connection

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            user = db_connection.get_user_by_email("nonexistent@test.com")
            assert user is None

    def test_create_duplicate_user_raises(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            db_connection.create_user("João", "joao@test.com", "hash1")
            with pytest.raises(Exception):
                db_connection.create_user("Outro", "joao@test.com", "hash2")


class TestFeedbackNoticia:
    def test_inserir_feedback_noticia_and_get_historico(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            # Create a user first (FK requirement)
            db_connection.create_user("Test User", "test@test.com", "hash")

            db_connection.inserir_feedback_noticia(
                titulo="Notícia Teste",
                descricao="Descrição da notícia teste",
                categoria="tecnologia",
                n_pal_titulo=2,
                n_pal_desc=4,
                sentimento=1,
                dia_semana=2,
                hora=14,
                popularidade_real="Alta",
                previsao_ia="Média",
                utilizador_id=1,
            )

            historico = db_connection.get_historico_noticias(1)
            assert len(historico) == 1
            assert historico[0]["Titulo_Input"] == "Notícia Teste"
            assert historico[0]["Popularidade_Real"] == "Alta"
            assert historico[0]["Previsao_IA"] == "Média"

    def test_get_historico_noticias_empty(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            historico = db_connection.get_historico_noticias(999)
            assert historico == []


class TestFeedbackSocial:
    def test_inserir_feedback_social_and_get_historico(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            db_connection.create_user("Test User", "test@test.com", "hash")

            db_connection.inserir_feedback_social(
                texto_post="Post sobre IA",
                seguidores=1000,
                likes=50,
                comentarios=10,
                mes=6,
                dia_semana=3,
                hora=10,
                n_hashtags=3,
                n_palavras=20,
                popularidade_real="Média",
                previsao_ia="Baixa",
                utilizador_id=1,
            )

            historico = db_connection.get_historico_social(1)
            assert len(historico) == 1
            assert historico[0]["Texto_Post"] == "Post sobre IA"
            assert historico[0]["Popularidade_Real"] == "Média"
            assert historico[0]["Seguidores"] == 1000

    def test_get_historico_social_empty(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            historico = db_connection.get_historico_social(999)
            assert historico == []


class TestGetMediasPopularidade:
    def test_get_medias_popularidade(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)

        # Insert some test data into Dataset_Social_Real
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Dataset_Social_Real (Post_ID_Social, Likes, Popularidade_Real) VALUES (?, ?, ?)",
            ("post1", 100, "alta"),
        )
        cursor.execute(
            "INSERT INTO Dataset_Social_Real (Post_ID_Social, Likes, Popularidade_Real) VALUES (?, ?, ?)",
            ("post2", 200, "alta"),
        )
        cursor.execute(
            "INSERT INTO Dataset_Social_Real (Post_ID_Social, Likes, Popularidade_Real) VALUES (?, ?, ?)",
            ("post3", 50, "baixa"),
        )
        conn.commit()
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            medias = db_connection.get_medias_popularidade()
            assert "alta" in medias
            assert "baixa" in medias
            assert medias["alta"] == 150.0  # (100 + 200) / 2
            assert medias["baixa"] == 50.0

    def test_get_medias_popularidade_empty(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            medias = db_connection.get_medias_popularidade()
            assert medias == {}


class TestExecuteQuery:
    def test_execute_query_fetch_one(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            db_connection.create_user("Query Test", "query@test.com", "hash")
            result = db_connection.execute_query(
                "SELECT * FROM Utilizadores WHERE Email = ?",
                ("query@test.com",),
                fetch_one=True,
            )
            assert result is not None
            assert result["Nome"] == "Query Test"

    def test_execute_query_fetch_all(self, tmp_path):
        from app import db_connection
        import sqlite3

        db_file = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_file, timeout=10)
        conn.executescript(SCHEMA)
        conn.close()

        with patch.object(db_connection, "DB_PATH", db_file):
            db_connection.create_user("User 1", "u1@test.com", "h1")
            db_connection.create_user("User 2", "u2@test.com", "h2")
            results = db_connection.execute_query(
                "SELECT * FROM Utilizadores", fetch_all=True
            )
            assert len(results) == 2
