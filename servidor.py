from flask import Flask, render_template, request, jsonify
import pandas as pd
import joblib
import os
from datetime import datetime
import db_connection

app = Flask(__name__)

# 1. Carregar o Modelo
base_path = os.path.dirname(__file__)
path_modelo = os.path.join(base_path, "models", "modelo_portugues_plus.pkl")

try:
    modelo = joblib.load(path_modelo)
    print(f"✅ Modelo carregado do caminho: {path_modelo}")
except Exception as e:
    print(f"❌ Erro fatal ao carregar o modelo: {e}")
    modelo = None

# ==========================================
# 2. MOTOR DE NLP - ANALISADOR LÉXICO AVANÇADO
# ==========================================
PAL_POS = [
    "vitória", "excelente", "positivo", "feliz", "bom", "ganha", "recorde", 
    "sucesso", "cresce", "lucro", "avanço", "melhora", "aprova", "recuperação", 
    "alta", "investimento", "acordo", "crescimento", "vantagem"
]

PAL_NEG = [
    "crise", "mau", "queda", "derrota", "trágico", "pior", "problema", 
    "falha", "rombo", "desemprego", "tensão", "prejuízo", "crime", "morte", 
    "risco", "baixa", "greve", "inflação", "polémica", "violência"
]

EXCECOES_NEGATIVAS = [
    "crise cresce", "desemprego sobe", "desemprego aumenta", "não ganha", 
    "não é bom", "lucro cai", "risco aumenta", "problema agrava", 
    "inflação sobe", "tensão aumenta", "sem acordo", "recuperação falha"
]

EXCECOES_POSITIVAS = [
    "desemprego cai", "desemprego desce", "crise diminui", "inflação desce", 
    "não é mau", "risco diminui", "problema resolvido", "tensão desce",
    "fim da greve", "bate recorde"
]

def analisar_sentimento(txt):
    if not txt: return 0
    t = txt.lower()
    
    pontuacao = 0
    
    # PASSO 1: Procurar Expressões Compostas (Têm prioridade máxima)
    for exp in EXCECOES_NEGATIVAS:
        if exp in t:
            pontuacao -= 2
            t = t.replace(exp, "") # Remove da frase para não ler as palavras soltas depois
            
    for exp in EXCECOES_POSITIVAS:
        if exp in t:
            pontuacao += 2
            t = t.replace(exp, "")

    # PASSO 2: Procurar Palavras Soltas (Valem 1 ponto)
    pontuacao += sum(p in t for p in PAL_POS)
    pontuacao -= sum(p in t for p in PAL_NEG)
    
    # PASSO 3: Limitar o score para não criar valores absurdos que confundam a IA
    if pontuacao > 5: pontuacao = 5
    if pontuacao < -5: pontuacao = -5
    
    return pontuacao

# ==========================================
# 3. ROTAS DO SERVIDOR FLASK
# ==========================================
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/prever', methods=['POST'])
def prever():
    dados_recebidos = request.json
    
    titulo = dados_recebidos.get('titulo', '')
    descricao = dados_recebidos.get('descricao', '')
    categoria = dados_recebidos.get('categoria', 'geral')
    data_str = dados_recebidos.get('data', '')
    hora_str = dados_recebidos.get('hora', '')
    
    # Processar Texto
    n_titulo = len(titulo.split())
    n_desc = len(descricao.split())
    sent = analisar_sentimento(descricao)
    
    # Processar Data e Hora do formulário
    try:
        data_obj = datetime.strptime(data_str, "%Y-%m-%d")
        dia_semana = data_obj.weekday()
    except:
        dia_semana = datetime.now().weekday()
        
    try:
        hora_int = int(hora_str.split(':')[0])
    except:
        hora_int = datetime.now().hour
    
    dados_modelo = {
        "n_palavras_titulo": n_titulo,
        "n_palavras_desc": n_desc,
        "sentimento": sent,
        "dia_semana": dia_semana,
        "hora": hora_int,
        "categoria": categoria
    }
    
    try:
        df_input = pd.DataFrame([dados_modelo])
        previsao = modelo.predict(df_input)[0]
        
        # Guardar dados para o feedback
        dados_modelo['titulo'] = titulo
        dados_modelo['descricao'] = descricao
        
        return jsonify({
            "sucesso": True, 
            "previsao": previsao,
            "dados_salvos": dados_modelo
        })
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})

@app.route('/feedback', methods=['POST'])
def feedback():
    dados_feedback = request.json
    try:
        db_connection.salvar_feedback(dados_feedback['dados'], dados_feedback['realidade'])
        return jsonify({"sucesso": True})
    except Exception as e:
        return jsonify({"sucesso": False, "erro": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)