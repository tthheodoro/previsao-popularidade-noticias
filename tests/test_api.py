"""Tests for Flask API endpoints (app.servidor)."""

import os
os.environ["SECRET_KEY"] = "test_key_for_testing"

import sqlite3
import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
import jwt


SCHEMA = """
CREATE TABLE IF NOT EXISTS Utilizadores (
    ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Nome TEXT NOT NULL,
    Email TEXT UNIQUE NOT NULL,
    Password_Hash TEXT NOT NULL,
    Data_Criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Noticias (
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

CREATE TABLE IF NOT EXISTS Feedback (
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

CREATE TABLE IF NOT EXISTS Feedback_Social (
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

CREATE TABLE IF NOT EXISTS Dataset_Social_Real (
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


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Set up a temp SQLite database and disable rate limiting for all tests."""
    from app import db_connection
    from app.servidor import app as flask_app

    db_file = str(tmp_path / "test_api.db")
    conn = sqlite3.connect(db_file, timeout=10)
    conn.executescript(SCHEMA)
    conn.close()

    with patch.object(db_connection, "DB_PATH", db_file):
        # Clear the rate limiter's in-memory storage between tests
        try:
            flask_app.limiter._storage.clear()
        except (AttributeError, Exception):
            pass
        yield


@pytest.fixture
def client():
    """Create Flask test client."""
    from app.servidor import app
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_token(client):
    """Register a user and return a valid JWT token."""
    from app.servidor import app as flask_app
    import bcrypt

    # Insert user directly into the DB to avoid rate limiting on register endpoint
    from app import db_connection
    email = "test@example.com"
    password = "testpassword123"
    salt = bcrypt.gensalt()
    pwd_hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
    db_connection.create_user("Test User", email, pwd_hash)

    # Login
    resp = client.post("/api/login", json={
        "email": email,
        "password": password,
    })
    data = resp.get_json()
    assert data["sucesso"] is True, f"Login failed: {data}"
    return data["token"]


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "noticias" in data["models"]
        assert "social" in data["models"]


class TestHomeEndpoint:
    def test_home_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200


class TestRegistar:
    def test_registar_valid_data(self, client):
        resp = client.post("/api/registar", json={
            "nome": "João Silva",
            "email": "joao@example.com",
            "password": "securepass123",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["sucesso"] is True

    def test_registar_missing_fields(self, client):
        resp = client.post("/api/registar", json={
            "nome": "João",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["sucesso"] is False

    def test_registar_invalid_email(self, client):
        resp = client.post("/api/registar", json={
            "nome": "João",
            "email": "not-an-email",
            "password": "securepass123",
        })
        assert resp.status_code == 400

    def test_registar_short_password(self, client):
        resp = client.post("/api/registar", json={
            "nome": "João",
            "email": "joao@example.com",
            "password": "123",
        })
        assert resp.status_code == 400

    def test_registar_duplicate_email(self, client):
        from app import db_connection
        import bcrypt

        # Insert user directly to test duplicate handling
        salt = bcrypt.gensalt()
        pwd_hash = bcrypt.hashpw(b"securepass123", salt).decode("utf-8")
        db_connection.create_user("João", "joao@example.com", pwd_hash)

        # Now try to register with the same email via the API
        resp = client.post("/api/registar", json={
            "nome": "João",
            "email": "joao@example.com",
            "password": "securepass123",
        })
        assert resp.status_code == 400


class TestLogin:
    def test_login_valid_credentials(self, client):
        from app import db_connection
        import bcrypt

        # Insert user directly to avoid rate limiting
        email = "login@example.com"
        salt = bcrypt.gensalt()
        pwd_hash = bcrypt.hashpw(b"testpass123", salt).decode("utf-8")
        db_connection.create_user("Test User", email, pwd_hash)

        resp = client.post("/api/login", json={
            "email": email,
            "password": "testpass123",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["sucesso"] is True
        assert "token" in data
        assert data["nome"] == "Test User"

    def test_login_wrong_password(self, client):
        from app import db_connection
        import bcrypt

        email = "login2@example.com"
        salt = bcrypt.gensalt()
        pwd_hash = bcrypt.hashpw(b"correctpass", salt).decode("utf-8")
        db_connection.create_user("Test User", email, pwd_hash)

        resp = client.post("/api/login", json={
            "email": email,
            "password": "wrongpass",
        })
        assert resp.status_code == 401
        data = resp.get_json()
        assert data["sucesso"] is False

    def test_login_nonexistent_email(self, client):
        resp = client.post("/api/login", json={
            "email": "noone@example.com",
            "password": "whatever",
        })
        assert resp.status_code == 401

    def test_login_no_data(self, client):
        resp = client.post("/api/login", json={})
        assert resp.status_code == 400


class TestPrever:
    def test_prever_without_auth(self, client):
        resp = client.post("/prever", data={
            "titulo": "Teste",
            "descricao": "Descrição teste",
        })
        assert resp.status_code == 401
        data = resp.get_json()
        assert "Token em falta" in data["erro"]

    def test_prever_with_auth_no_model(self, client, auth_token):
        """When models aren't loaded, should return 503."""
        from app import servidor

        original = servidor.modelo_noticias
        servidor.modelo_noticias = None
        try:
            resp = client.post(
                "/prever",
                data={"titulo": "Teste", "descricao": "Descrição teste"},
                headers={"Authorization": f"Bearer {auth_token}"},
            )
            assert resp.status_code == 503
            data = resp.get_json()
            assert data["sucesso"] is False
        finally:
            servidor.modelo_noticias = original

    def test_prever_social_without_auth(self, client):
        resp = client.post("/prever_social", data={
            "texto_social": "Post teste",
            "seguidores": "100",
            "likes": "10",
            "comentarios": "5",
        })
        assert resp.status_code == 401


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        resp = client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert "X-XSS-Protection" in resp.headers
