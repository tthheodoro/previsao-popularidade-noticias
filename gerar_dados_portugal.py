# ============================================================
# Recolha de Notícias -> SQL SERVER 🛢️
# ============================================================
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
import db_connection  # <--- O NOSSO NOVO MÓDULO

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

FEEDS = {
    "RTP": {
        "politica": "https://www.rtp.pt/noticias/rss/politica",
        "economia": "https://www.rtp.pt/noticias/rss/economia",
        "cultura": "https://www.rtp.pt/noticias/rss/cultura",
        "desporto": "https://www.rtp.pt/noticias/rss/desporto",
        "pais": "https://www.rtp.pt/noticias/rss/pais",
    },
    "Publico": { "geral": "https://feeds.publico.pt/rss/publico/ultimas" },
    "Observador": { "geral": "https://observador.pt/feed" },
}

PAL_POS = ["vitória", "excelente", "positivo", "cresce", "feliz", "bom", "ganha", "recorde", "sucesso"]
PAL_NEG = ["crise", "mau", "queda", "derrota", "trágico", "pior", "problema", "falha", "rombo"]

def analisar_sentimento(txt):
    if not isinstance(txt, str): return 0
    t = txt.lower()
    return sum(p in t for p in PAL_POS) - sum(p in t for p in PAL_NEG)

def fetch_xml(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        return r.text if r.status_code == 200 else None
    except:
        return None

def clean_html(text):
    if not text: return ""
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()

def recolher_noticias():
    registos = []
    print("🚀 A iniciar recolha de RSS...")
    
    for fonte, categorias in FEEDS.items():
        for categoria, url in categorias.items():
            xml = fetch_xml(url)
            if not xml: continue
            
            soup = BeautifulSoup(xml, "xml")
            items = soup.find_all("item")
            
            for it in items:
                try:
                    titulo = it.title.text.strip()
                    desc = clean_html(it.description.text)
                    link = it.link.text.strip()
                    pub_date = it.pubDate.text.strip() if it.pubDate else str(datetime.now())
                    
                    registos.append({
                        "titulo": titulo, "descricao": desc, "link": link,
                        "data_publicacao": pub_date, "fonte": fonte, "categoria": categoria
                    })
                except: continue

    df = pd.DataFrame(registos).drop_duplicates(subset=["link"])
    return df

def enriquecer(df):
    if df.empty: return df
    df["n_palavras_titulo"] = df["titulo"].apply(lambda x: len(str(x).split()))
    df["n_palavras_desc"] = df["descricao"].apply(lambda x: len(str(x).split()))
    df["data_publicacao"] = pd.to_datetime(df["data_publicacao"], errors="coerce")
    df["dia_semana"] = df["data_publicacao"].dt.weekday 
    df["hora"] = df["data_publicacao"].dt.hour 
    df["sentimento"] = df["descricao"].apply(analisar_sentimento)
    return df.dropna()

if __name__ == "__main__":
    df_raw = recolher_noticias()
    df_final = enriquecer(df_raw)
    
    print(f"📊 Notícias recolhidas: {len(df_final)}")
    
    # AQUI ESTÁ A MUDANÇA: Guardar no SQL Server via db_connection
    if not df_final.empty:
        db_connection.salvar_noticias_batch(df_final)
    else:
        print("⚠️ Nenhuma notícia nova para guardar.")