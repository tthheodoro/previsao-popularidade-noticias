"""
API Principal (Servidor Flask) | AI Popularity Predictor
"""

from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import pandas as pd
import numpy as np
import joblib
import os
import sys
import cv2
import re
import logging
from datetime import datetime, timedelta
from app import db_connection
from app.utils.sentimento import analisar_sentimento
import bcrypt
import jwt
from functools import wraps
from dotenv import load_dotenv
import torch
from torchvision.models import resnet18, ResNet18_Weights
from PIL import Image
from io import BytesIO

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))

app = Flask(__name__,
            template_folder=os.path.join(PROJECT_ROOT, 'templates'),
            static_folder=os.path.join(PROJECT_ROOT, 'static'))

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload

if not app.config['SECRET_KEY']:
    raise RuntimeError("SECRET_KEY not set in environment variables")

# Rate limiting
limiter = Limiter(get_remote_address, app=app, default_limits=["200 per minute"])

# CORS — allow all origins for HF Spaces
CORS(app)

# Cached resources
modelo_noticias = None
modelo_social = None
face_cascade = None
extrator_visao = None
preprocess_visao = None


def sanitizar_texto(texto):
    """Remove HTML tags and limit text length."""
    if not texto:
        return ""
    texto = str(texto)[:5000]  # Max 5000 chars
    texto = re.sub(r'<[^>]+>', '', texto)  # Remove HTML tags
    texto = re.sub(r'javascript:', '', texto, flags=re.IGNORECASE)
    return texto.strip()


def carregar_recursos():
    """Load ML models, face detector, and vision extractor at startup."""
    global modelo_noticias, modelo_social, face_cascade, extrator_visao, preprocess_visao

    models_dir = os.path.join(PROJECT_ROOT, "models")

    # Download models from GitHub if not present locally
    import urllib.request
    github_base = "https://raw.githubusercontent.com/tthheodoro/previsao-popularidade-noticias/main/models"
    for model_file in ["modelo_noticias.pkl", "modelo_social.pkl"]:
        local_path = os.path.join(models_dir, model_file)
        if not os.path.exists(local_path):
            try:
                os.makedirs(models_dir, exist_ok=True)
                url = f"{github_base}/{model_file}"
                logger.info(f"Downloading {model_file} from GitHub...")
                urllib.request.urlretrieve(url, local_path)
                logger.info(f"Downloaded {model_file}")
            except Exception as e:
                logger.warning(f"Could not download {model_file}: {e}")

    try:
        modelo_noticias = joblib.load(os.path.join(models_dir, "modelo_noticias.pkl"))
        modelo_social = joblib.load(os.path.join(models_dir, "modelo_social.pkl"))
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        logger.info("Models loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load ML models: {e}")
        modelo_noticias = None
        modelo_social = None
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Load ResNet18 vision extractor (same config as treinar_social.py)
    try:
        weights = ResNet18_Weights.DEFAULT
        modelo_visao = resnet18(weights=weights)
        extrator_visao = torch.nn.Sequential(*list(modelo_visao.children())[:-1])
        extrator_visao.eval()
        preprocess_visao = weights.transforms()
        logger.info("ResNet18 vision extractor loaded successfully")
    except Exception as e:
        logger.warning(f"Could not load ResNet18 vision extractor: {e}")
        extrator_visao = None
        preprocess_visao = None


# Ensure database tables exist before loading models
logger.info("Ensuring database tables exist...")
db_connection.ensure_tables()
logger.info("Database ready.")

carregar_recursos()


def token_obrigatorio(f):
    """JWT authentication decorator."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2:
                token = parts[1]
        if not token:
            return jsonify({'sucesso': False, 'erro': 'Token em falta!'}), 401
        try:
            dados = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = dados['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'sucesso': False, 'erro': 'Token expirado!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'sucesso': False, 'erro': 'Token inválido!'}), 401
        return f(current_user_id, *args, **kwargs)
    return decorated


def obter_user_id_opcional():
    """Extract user ID from optional JWT token."""
    if 'Authorization' in request.headers:
        try:
            parts = request.headers['Authorization'].split(" ")
            if len(parts) == 2:
                dados = jwt.decode(parts[1], app.config['SECRET_KEY'], algorithms=["HS256"])
                return dados['user_id']
        except:
            pass
    return None


# --- SECURITY HEADERS ---

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


# --- ROUTES ---

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login-page')
def pagina_login():
    return render_template('login.html')


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok", "models": {
        "noticias": modelo_noticias is not None,
        "social": modelo_social is not None,
        "vision": extrator_visao is not None
    }})


@app.route('/prever', methods=['POST'])
@token_obrigatorio
@limiter.limit("30 per minute")
def prever(current_user_id):
    if modelo_noticias is None:
        return jsonify({"sucesso": False, "erro": "Modelo não disponível."}), 503
    try:
        titulo = sanitizar_texto(request.form.get('titulo', ''))
        descricao = sanitizar_texto(request.form.get('descricao', ''))
        categoria = sanitizar_texto(request.form.get('categoria', 'geral'))

        if not titulo:
            return jsonify({"sucesso": False, "erro": "O título é obrigatório."}), 400
        if not descricao:
            return jsonify({"sucesso": False, "erro": "A descrição é obrigatória."}), 400

        sent = analisar_sentimento(titulo + " " + descricao)

        # Read date/time from form, fallback to current time
        now = datetime.now()
        try:
            dia = int(request.form.get('data_dia', now.day))
            mes = int(request.form.get('data_mes', now.month))
            ano = int(request.form.get('data_ano', now.year))
            hora = int(request.form.get('hora_h', now.hour))
            dt = datetime(ano, mes, dia, hora)
            dia_semana = dt.weekday()
        except (ValueError, TypeError):
            dia_semana = now.weekday()
            hora = now.hour

        df_input = pd.DataFrame([{
            "n_palavras_titulo": len(titulo.split()) if titulo else 0,
            "n_palavras_desc": len(descricao.split()) if descricao else 0,
            "sentimento": sent,
            "dia_semana": dia_semana,
            "hora": hora,
            "categoria": categoria
        }])

        previsao = modelo_noticias.predict(df_input)[0]
        return jsonify({"sucesso": True, "previsao": previsao})
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"sucesso": False, "erro": "Erro ao processar previsão."}), 500


@app.route('/prever_social', methods=['POST'])
@token_obrigatorio
@limiter.limit("30 per minute")
def prever_social(current_user_id):
    if modelo_social is None:
        return jsonify({"sucesso": False, "erro": "Modelo não disponível."}), 503
    try:
        texto_post = sanitizar_texto(request.form.get('texto_social', ''))
        seguidores_raw = request.form.get('seguidores', '')
        likes_raw = request.form.get('likes', '')
        comentarios_raw = request.form.get('comentarios', '')

        if not texto_post:
            return jsonify({"sucesso": False, "erro": "O texto da publicação é obrigatório."}), 400
        if not seguidores_raw or seguidores_raw == '':
            return jsonify({"sucesso": False, "erro": "O número de seguidores é obrigatório."}), 400
        if likes_raw == '' or likes_raw is None:
            return jsonify({"sucesso": False, "erro": "O número de likes é obrigatório."}), 400
        if comentarios_raw == '' or comentarios_raw is None:
            return jsonify({"sucesso": False, "erro": "O número de comentários é obrigatório."}), 400

        seguidores = max(0, int(seguidores_raw))
        likes = max(0, int(likes_raw))
        comentarios = max(0, int(comentarios_raw))

        foto = request.files.get('imagem_post')
        n_rostos, brilho = 0, 127
        features_visuais = np.zeros(512)

        if foto and foto.filename:
            file_bytes = foto.read()

            # OpenCV processing (faces + brightness)
            file_bytes_np = np.frombuffer(file_bytes, np.uint8)
            img_cv = cv2.imdecode(file_bytes_np, cv2.IMREAD_COLOR)
            if img_cv is not None:
                gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                brilho = int(np.mean(gray))
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                n_rostos = len(faces)

            # ResNet18 feature extraction (same preprocessing as treinar_social.py)
            if extrator_visao is not None:
                try:
                    img_pil = Image.open(BytesIO(file_bytes)).convert('RGB')
                    tensor = preprocess_visao(img_pil).unsqueeze(0)
                    with torch.no_grad():
                        features_visuais = extrator_visao(tensor).squeeze().numpy()
                except Exception as e:
                    logger.warning(f"ResNet18 feature extraction failed, using zeros: {e}")
            else:
                logger.warning("ResNet18 not loaded, using zero visual features")
        else:
            logger.info("No image provided, using zero visual features")

        # 5 numeric features + 512 visual features = 517 total (matches treinar_social.py)
        input_final = np.concatenate([
            np.array([[likes, comentarios, seguidores, n_rostos, brilho]]),
            features_visuais.reshape(1, -1)
        ], axis=1)
        resultado_final = modelo_social.predict(input_final)[0]

        taxa_envolvimento = (likes / seguidores) * 100 if seguidores > 0 else 0
        mensagem_calibracao = ""

        if 0 < seguidores < 5000:
            if taxa_envolvimento >= 5.0:
                resultado_final = "Alta"
                mensagem_calibracao = f" | IA adaptada: Taxa de interação excelente ({taxa_envolvimento:.1f}%)."
            elif taxa_envolvimento >= 2.0 and resultado_final.lower() == "baixa":
                resultado_final = "Média"
                mensagem_calibracao = f" | IA adaptada: Taxa de interação saudável ({taxa_envolvimento:.1f}%)."
        elif seguidores >= 100000:
            if taxa_envolvimento < 0.2 and resultado_final.lower() == "alta":
                resultado_final = "Baixa"
                mensagem_calibracao = f" | IA ajustou: Taxa de interação ({taxa_envolvimento:.2f}%) insuficiente."

        medias_reais = db_connection.get_medias_popularidade()
        media_prevista = medias_reais.get(resultado_final.lower(), 0)
        est_txt = f" | Média histórica real: {int(media_prevista):,} likes." if media_prevista > 0 else ""

        contexto = f"IA detetou {n_rostos} rostos e brilho de {brilho}/255.{mensagem_calibracao}{est_txt}"

        sugestoes = []
        if resultado_final.lower() in ['baixa', 'média', 'media']:
            if n_rostos == 0:
                sugestoes.append("Dica: Notícias com rostos geram mais empatia.")
            if brilho < 90:
                sugestoes.append("Dica: Tente uma imagem com mais luminosidade.")
            if len(texto_post.split()) < 15:
                sugestoes.append("Dica: Desenvolva a narrativa do post.")
            if texto_post.count('#') < 3:
                sugestoes.append("Dica: Adicione 3 a 5 hashtags relevantes.")

        return jsonify({
            "sucesso": True,
            "previsao": resultado_final,
            "contexto_ia": contexto,
            "sugestoes": sugestoes
        })
    except Exception as e:
        logger.error(f"Social prediction error: {e}")
        return jsonify({"sucesso": False, "erro": "Erro ao processar previsão social."}), 500


@app.route('/api/registar', methods=['POST'])
@limiter.limit("5 per minute")
def registar():
    try:
        dados = request.json
        if not dados or not dados.get('nome') or not dados.get('email') or not dados.get('password'):
            return jsonify({"sucesso": False, "erro": "Dados incompletos."}), 400

        nome = sanitizar_texto(dados['nome'])
        email = dados.get('email', '').strip().lower()
        password = dados['password']

        if len(password) < 6:
            return jsonify({"sucesso": False, "erro": "Password deve ter pelo menos 6 caracteres."}), 400

        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return jsonify({"sucesso": False, "erro": "Email inválido."}), 400

        salt = bcrypt.gensalt()
        pwd_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        db_connection.create_user(nome, email, pwd_hash)
        logger.info(f"New user registered: {email}")
        return jsonify({"sucesso": True, "mensagem": "Conta criada com sucesso!"})
    except Exception as e:
        logger.error(f"Registration error: {type(e).__name__}: {e}")
        return jsonify({"sucesso": False, "erro": "Erro ao criar conta. Email já existe?"}), 400


@app.route('/api/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    try:
        dados = request.json
        if not dados:
            return jsonify({"sucesso": False, "erro": "Dados inválidos."}), 400

        email_limpo = dados.get('email', '').strip().lower()
        password_inserida = dados.get('password', '')

        user = db_connection.get_user_by_email(email_limpo)

        if not user:
            return jsonify({"sucesso": False, "erro": "Email ou password incorretos."}), 401

        hash_db = user['password_hash'].strip()

        if bcrypt.checkpw(password_inserida.encode('utf-8'), hash_db.encode('utf-8')):
            token = jwt.encode(
                {"user_id": user['id'], "exp": datetime.utcnow() + timedelta(hours=24)},
                app.config['SECRET_KEY'],
                algorithm="HS256"
            )
            logger.info(f"User logged in: {email_limpo}")
            return jsonify({"sucesso": True, "token": token, "nome": user['nome'], "email": email_limpo})
        else:
            return jsonify({"sucesso": False, "erro": "Email ou password incorretos."}), 401

    except Exception as e:
        logger.error(f"Login error: {type(e).__name__}: {e}")
        return jsonify({"sucesso": False, "erro": "Erro interno."}), 500


@app.route('/api/perfil', methods=['GET'])
@token_obrigatorio
def gerir_perfil(current_user_id):
    user = db_connection.get_user_profile(current_user_id)
    if not user:
        return jsonify({"sucesso": False, "erro": "Utilizador não encontrado."}), 404
    return jsonify({"sucesso": True, "nome": user['nome'], "email": user['email']})


@app.route('/feedback', methods=['POST'])
@token_obrigatorio
@limiter.limit("30 per minute")
def guardar_feedback(current_user_id):
    try:
        dados = request.json
        if not dados:
            return jsonify({"sucesso": False, "erro": "Dados inválidos."}), 400

        popularidade_real = sanitizar_texto(dados.get('popularidade_real', ''))
        previsao_ia = sanitizar_texto(dados.get('previsao_ia', 'N/A'))

        if popularidade_real not in ['Alta', 'Média', 'Baixa']:
            return jsonify({"sucesso": False, "erro": "Popularidade inválida."}), 400

        agora = datetime.now()
        dia_semana = agora.weekday()
        hora = agora.hour

        if 'titulo' in dados:
            titulo = sanitizar_texto(dados.get('titulo', ''))
            descricao = sanitizar_texto(dados.get('descricao', ''))
            categoria = sanitizar_texto(dados.get('categoria', 'geral'))

            n_pal_titulo = len(titulo.split()) if titulo else 0
            n_pal_desc = len(descricao.split()) if descricao else 0
            sentimento = analisar_sentimento(titulo + " " + descricao)

            db_connection.inserir_feedback_noticia(
                titulo, descricao, categoria, n_pal_titulo, n_pal_desc,
                sentimento, dia_semana, hora, popularidade_real, previsao_ia, current_user_id
            )
            mensagem_sucesso = "Feedback de Notícia guardado com sucesso!"
        else:
            texto_post = sanitizar_texto(dados.get('texto_post', ''))
            try:
                seguidores = max(0, int(dados.get('seguidores', 0)))
                likes = max(0, int(dados.get('likes', 0)))
                comentarios = max(0, int(dados.get('comentarios', 0)))
            except (ValueError, TypeError):
                seguidores, likes, comentarios = 0, 0, 0

            n_palavras = len(texto_post.split()) if texto_post else 0
            n_hashtags = texto_post.count('#') if texto_post else 0
            mes = agora.month

            db_connection.inserir_feedback_social(
                texto_post, seguidores, likes, comentarios, mes, dia_semana, hora,
                n_hashtags, n_palavras, popularidade_real, previsao_ia, current_user_id
            )
            mensagem_sucesso = "Feedback Social guardado com sucesso!"

        logger.info(f"Feedback saved by user {current_user_id}")
        return jsonify({"sucesso": True, "mensagem": mensagem_sucesso})

    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({"sucesso": False, "erro": "Erro ao guardar feedback."}), 500


@app.route('/api/historico', methods=['GET'])
@token_obrigatorio
def obter_historico(current_user_id):
    try:
        noticias = db_connection.get_historico_noticias(current_user_id)
        social = db_connection.get_historico_social(current_user_id)

        historico = []

        for n in noticias:
            data_val = n['datafeedback']
            data_str = data_val.strftime("%Y-%m-%d %H:%M") if hasattr(data_val, 'strftime') else str(data_val)[:16] if data_val else ""

            historico.append({
                "tipo": "noticia",
                "titulo": n['titulo_input'] or "Sem Título",
                "detalhe": f"Categoria: {n['categoria_input']}",
                "feedback": n['popularidade_real'],
                "data": data_str,
                "previsao_ia": n['previsao_ia'] or "N/A"
            })

        for s in social:
            likes_val = s['likes'] if s['likes'] is not None else 0
            coments_val = s['comentarios'] if s['comentarios'] is not None else 0
            
            data_val = s['data_registo']
            data_str = data_val.strftime("%Y-%m-%d %H:%M") if hasattr(data_val, 'strftime') else str(data_val)[:16] if data_val else ""
            
            historico.append({
                "tipo": "social",
                "titulo": s['texto_post'] or "Post sem texto",
                "detalhe": f"Seguidores: {s['seguidores']}  •  Likes: {likes_val}  •  Comentários: {coments_val}",
                "feedback": s['popularidade_real'],
                "data": data_str,
                "previsao_ia": s['previsao_ia'] or "N/A"
            })

        historico = sorted(historico, key=lambda x: x['data'], reverse=True)[:100]  # Limit to 100 items
        return jsonify({"sucesso": True, "historico": historico})

    except Exception as e:
        logger.error(f"History error: {e}")
        return jsonify({"sucesso": False, "erro": "Não foi possível carregar o histórico."}), 500


@app.errorhandler(413)
def too_large(e):
    return jsonify({"sucesso": False, "erro": "Ficheiro demasiado grande (máx. 5MB)."}), 413


@app.errorhandler(404)
def not_found(e):
    return jsonify({"sucesso": False, "erro": "Rota não encontrada."}), 404


@app.errorhandler(429)
def rate_limited(e):
    return jsonify({"sucesso": False, "erro": "Demasiados pedidos. Tente novamente mais tarde."}), 429


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
