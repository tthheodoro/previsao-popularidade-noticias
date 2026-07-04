"""
Database Connection Manager
---------------------------
Supabase PostgreSQL connection pooling and optimized queries.
"""

import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

_lock = None  # No longer needed for PostgreSQL


def get_database_url():
    """Read DATABASE_URL from environment at call time (not import time)."""
    import logging
    logger = logging.getLogger(__name__)
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    # Remove pgbouncer parameter (psycopg2 doesn't support it)
    url = url.replace('?pgbouncer=true', '').replace('&pgbouncer=true', '')
    # Debug: show structure without exposing password
    from urllib.parse import urlparse
    parsed = urlparse(url)
    logger.info(f"DB host: {parsed.hostname}, port: {parsed.port}, user: {parsed.username}, db: {parsed.path}")
    if not url.startswith('postgresql'):
        raise RuntimeError(f"DATABASE_URL has invalid format: starts with '{url[:10]}...'")
    return url


def ensure_tables():
    """Create tables if they don't exist (auto-init for fresh deployments)."""
    import logging
    logger = logging.getLogger(__name__)

    db_url = get_database_url()

    logger.info("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS utilizadores (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        data_criacao TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS noticias (
        id SERIAL PRIMARY KEY,
        titulo TEXT, descricao TEXT, link TEXT UNIQUE,
        datapublicacao TIMESTAMP, fonte TEXT, categoria TEXT,
        n_palavras_titulo INTEGER, n_palavras_desc INTEGER,
        dia_semana INTEGER, hora INTEGER, sentimento INTEGER,
        popularidade_real TEXT, datainsercao TIMESTAMP DEFAULT NOW()
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS feedback (
        id SERIAL PRIMARY KEY,
        titulo_input TEXT, descricao_input TEXT, categoria_input TEXT,
        n_palavras_titulo INTEGER, n_palavras_desc INTEGER,
        sentimento INTEGER, dia_semana INTEGER, hora INTEGER,
        popularidade_real TEXT, previsao_ia TEXT, utilizador_id INTEGER,
        datafeedback TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS feedback_social (
        id SERIAL PRIMARY KEY,
        texto_post TEXT, seguidores INTEGER, likes INTEGER,
        comentarios INTEGER, mes INTEGER, dia_semana INTEGER,
        hora INTEGER, n_hashtags INTEGER, n_palavras INTEGER,
        popularidade_real TEXT, previsao_ia TEXT, utilizador_id INTEGER,
        data_registo TIMESTAMP DEFAULT NOW(),
        FOREIGN KEY (utilizador_id) REFERENCES utilizadores(id)
    )''')

    cur.execute('''CREATE TABLE IF NOT EXISTS dataset_social_real (
        id SERIAL PRIMARY KEY,
        post_id_social TEXT UNIQUE, fonte TEXT, plataforma TEXT,
        texto_post TEXT, link_post TEXT, data_publicacao TEXT,
        likes INTEGER DEFAULT 0, comentarios INTEGER DEFAULT 0,
        partilhas INTEGER DEFAULT 0, popularidade_real TEXT,
        data_recolha TIMESTAMP DEFAULT NOW(),
        avaliado INTEGER DEFAULT 0, link_imagem TEXT,
        n_rostos INTEGER DEFAULT 0, brilho_imagem INTEGER DEFAULT 127,
        likes_12h INTEGER, likes_24h INTEGER, likes_48h INTEGER
    )''')

    conn.close()
    logger.info("Database tables ready.")


@contextmanager
def get_connection():
    """Get a PostgreSQL connection with automatic cleanup."""
    conn = psycopg2.connect(get_database_url())
    conn.autocommit = False
    try:
        yield conn
    finally:
        conn.close()


def execute_query(query, params=(), fetch_one=False, fetch_all=False):
    """Execute a query and return results safely."""
    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        if fetch_one:
            result = cur.fetchone()
            conn.commit()
            return result
        if fetch_all:
            result = cur.fetchall()
            conn.commit()
            return result
        conn.commit()
        return None


def execute_many(query, params_list):
    """Execute a batch insert/update."""
    with get_connection() as conn:
        cur = conn.cursor()
        cur.executemany(query, params_list)
        conn.commit()


def inserir_noticias_batch(df):
    """Batch insert news articles using executemany for performance."""
    if df.empty:
        return

    query = """
    INSERT INTO noticias
    (titulo, descricao, link, datapublicacao, fonte, categoria,
     n_palavras_titulo, n_palavras_desc, dia_semana, hora, sentimento, popularidade_real)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (link) DO NOTHING
    """

    params_list = [
        (row['titulo'], row['descricao'], row['link'], row['data_publicacao'],
         row['fonte'], row['categoria'], row['n_palavras_titulo'],
         row['n_palavras_desc'], row['dia_semana'], row['hora'],
         row['sentimento'], row['popularidade_real'])
        for _, row in df.iterrows()
    ]

    execute_many(query, params_list)


def upsert_social_real(post_data, fonte, plataforma, popularidade, avaliado):
    """Insert or update social media post data."""
    post_id = str(post_data.get('id', ''))
    if not post_id:
        return

    text = str(post_data.get('caption', ''))[:1000]
    link = str(post_data.get('url', ''))
    img_url = post_data.get('image_url', '')
    timestamp = post_data.get('timestamp', '')
    likes = int(post_data.get('likesCount', 0) or 0)
    comments = int(post_data.get('commentsCount', 0) or 0)
    n_rostos = int(post_data.get('n_rostos', 0) or 0)
    brilho = int(post_data.get('brilho', 127) or 127)

    with get_connection() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute("SELECT id, data_publicacao, likes_12h, likes_24h, likes_48h FROM dataset_social_real WHERE post_id_social = %s", (post_id,))
        row = cur.fetchone()

        import datetime
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if row:
            try:
                dt_pub = row['data_publicacao']
                if isinstance(dt_pub, str):
                    dt_pub = datetime.datetime.strptime(dt_pub, '%Y-%m-%d %H:%M:%S')
                horas_passadas = (datetime.datetime.now() - dt_pub).total_seconds() / 3600
            except Exception:
                horas_passadas = 0

            update_parts = ["likes = %s", "comentarios = %s", "popularidade_real = %s", "link_imagem = %s", "n_rostos = %s", "brilho_imagem = %s"]
            params = [likes, comments, popularidade, img_url, n_rostos, brilho]

            if horas_passadas >= 11 and row['likes_12h'] is None:
                update_parts.append("likes_12h = %s")
                params.append(likes)
            if horas_passadas >= 23 and row['likes_24h'] is None:
                update_parts.append("likes_24h = %s")
                params.append(likes)
            if horas_passadas >= 47:
                if row['likes_48h'] is None:
                    update_parts.append("likes_48h = %s")
                    params.append(likes)
                update_parts.append("avaliado = 1")

            sql = f"UPDATE dataset_social_real SET {', '.join(update_parts)} WHERE post_id_social = %s"
            params.append(post_id)
            cur.execute(sql, tuple(params))
        else:
            cur.execute("""
                INSERT INTO dataset_social_real
                (post_id_social, fonte, plataforma, texto_post, link_post, data_publicacao,
                 likes, comentarios, partilhas, popularidade_real, data_recolha, avaliado, link_imagem, n_rostos, brilho_imagem)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (post_id, fonte, plataforma, text, link, timestamp, likes, comments, 0, popularidade, now_str, avaliado, img_url, n_rostos, brilho))

        conn.commit()


def get_posts_para_checkpoint():
    """Get posts pending checkpoint updates."""
    query = """
    SELECT id, link_post, plataforma
    FROM dataset_social_real
    WHERE avaliado = 0
    AND (
        EXTRACT(EPOCH FROM (NOW() - data_publicacao::timestamp)) / 3600 BETWEEN 11 AND 15 OR
        EXTRACT(EPOCH FROM (NOW() - data_publicacao::timestamp)) / 3600 BETWEEN 23 AND 28 OR
        EXTRACT(EPOCH FROM (NOW() - data_publicacao::timestamp)) / 3600 >= 47
    )
    """
    import pandas as pd
    with get_connection() as conn:
        return pd.read_sql(query, conn)


def get_medias_popularidade():
    """Get average likes by popularity class for calibration."""
    query = "SELECT popularidade_real, AVG(likes::float) FROM dataset_social_real GROUP BY popularidade_real"
    results = execute_query(query, fetch_all=True)
    return {str(row['popularidade_real']).lower(): row['avg'] for row in results} if results else {}


def get_historico_noticias(user_id):
    """Get news history for a user."""
    query = """
        SELECT id, titulo_input, categoria_input, popularidade_real, datafeedback, previsao_ia
        FROM feedback
        WHERE utilizador_id = %s
        ORDER BY datafeedback DESC
        LIMIT 50
    """
    result = execute_query(query, (user_id,), fetch_all=True)
    return result if result else []


def get_historico_social(user_id):
    """Get social history for a user."""
    query = """
        SELECT id, texto_post, seguidores, popularidade_real, data_registo, likes, comentarios, previsao_ia
        FROM feedback_social
        WHERE utilizador_id = %s
        ORDER BY data_registo DESC
        LIMIT 50
    """
    result = execute_query(query, (user_id,), fetch_all=True)
    return result if result else []


def inserir_feedback_noticia(titulo, descricao, categoria, n_pal_titulo, n_pal_desc,
                             sentimento, dia_semana, hora, popularidade_real, previsao_ia, utilizador_id):
    """Insert news feedback."""
    query = """
    INSERT INTO feedback (titulo_input, descricao_input, categoria_input, n_palavras_titulo,
    n_palavras_desc, sentimento, dia_semana, hora, popularidade_real, previsao_ia, utilizador_id, datafeedback)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    execute_query(query, (titulo, descricao, categoria, n_pal_titulo, n_pal_desc,
                          sentimento, dia_semana, hora, popularidade_real, previsao_ia, utilizador_id))


def inserir_feedback_social(texto_post, seguidores, likes, comentarios, mes, dia_semana, hora,
                            n_hashtags, n_palavras, popularidade_real, previsao_ia, utilizador_id):
    """Insert social feedback."""
    query = """
    INSERT INTO feedback_social
    (texto_post, seguidores, likes, comentarios, mes, dia_semana, hora, n_hashtags, n_palavras, popularidade_real, previsao_ia, utilizador_id, data_registo)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
    """
    execute_query(query, (texto_post, seguidores, likes, comentarios, mes, dia_semana, hora,
                          n_hashtags, n_palavras, popularidade_real, previsao_ia, utilizador_id))


def get_user_by_email(email):
    """Get user credentials by email."""
    query = "SELECT id, nome, password_hash FROM utilizadores WHERE email = %s"
    return execute_query(query, (email,), fetch_one=True)


def create_user(nome, email, password_hash):
    """Create a new user."""
    query = "INSERT INTO utilizadores (nome, email, password_hash) VALUES (%s, %s, %s)"
    execute_query(query, (nome, email, password_hash))


def get_user_profile(user_id):
    """Get user profile."""
    query = "SELECT nome, email FROM utilizadores WHERE id = %s"
    return execute_query(query, (user_id,), fetch_one=True)


def carregar_dados_treino():
    """Load training data (news + feedback) for model training."""
    import pandas as pd
    with get_connection() as conn:
        try:
            df_noticias = pd.read_sql("SELECT * FROM noticias", conn)
        except Exception:
            df_noticias = pd.DataFrame()
        try:
            df_feedback = pd.read_sql("SELECT * FROM feedback", conn)
        except Exception:
            df_feedback = pd.DataFrame()
        return df_noticias, df_feedback


def carregar_dados_sociais_reais():
    """Load real social data for monitoring."""
    import pandas as pd
    with get_connection() as conn:
        try:
            return pd.read_sql("SELECT * FROM dataset_social_real", conn)
        except Exception:
            return pd.DataFrame()
