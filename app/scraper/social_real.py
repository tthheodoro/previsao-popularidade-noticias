"""
Social Media Scraper (Apify)
----------------------------
Extracts posts from Instagram and Facebook using Apify API.
Implements Gatekeeper pattern for checkpoint maturation.
"""

import sys
import os

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

import requests
from apify_client import ApifyClient
from app import db_connection
from datetime import datetime
import numpy as np
from dotenv import load_dotenv

load_dotenv(os.path.join(PROJECT_ROOT, '.env'))
token_apify = os.getenv('APIFY_TOKEN')
client = ApifyClient(token_apify)


def extrair_instagram(username, limite=5):
    """Extract new posts from Instagram profile."""
    run_input = {"username": [username], "resultsLimit": limite}
    run = client.actor("apify/instagram-post-scraper").call(run_input=run_input)
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def extrair_facebook(page_name, limite=5):
    """Extract new posts from Facebook page."""
    run_input = {
        "startUrls": [{"url": f"https://www.facebook.com/{page_name}"}],
        "resultsLimit": limite,
        "viewOption": "POSTS_RECENT"
    }
    run = client.actor("apify/facebook-posts-scraper").call(run_input=run_input)
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def extrair_posts_especificos(urls, rede):
    """Update specific posts by direct URL."""
    if not urls:
        return []

    actor = "apify/instagram-post-scraper" if rede == "instagram" else "apify/facebook-posts-scraper"

    if rede == "instagram":
        run_input = {
            "username": ["rtpnoticias"],
            "directUrls": urls,
            "resultsLimit": len(urls)
        }
    else:
        run_input = {"startUrls": [{"url": u} for u in urls]}

    run = client.actor(actor).call(run_input=run_input)
    return list(client.dataset(run["defaultDatasetId"]).iterate_items())


def tratar_data(p):
    """Normalize date format from Apify."""
    ts = p.get('timestamp') or p.get('date') or p.get('createdAt')
    if not ts:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        if 'T' in str(ts):
            return datetime.fromisoformat(str(ts).replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
    except:
        pass
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def calcular_popularidade(likes, comments, l_inf=50, l_sup=500):
    """Calculate popularity class based on engagement."""
    total = likes + comments
    if total >= l_sup:
        return "alta"
    if total <= l_inf:
        return "baixa"
    return "média"


def processar_posts(posts, fonte, rede):
    """Process a batch of posts and save to database."""
    for p in posts:
        likes = int(p.get('likesCount', p.get('likes', p.get('reactionsCount', 0)) or 0))
        comments = int(p.get('commentsCount', p.get('comments', 0) or 0))

        pr_sql = {
            'id': p.get('id', p.get('shortCode', str(np.random.randint(1e9)))),
            'likesCount': likes,
            'commentsCount': comments,
            'caption': (p.get('caption') or p.get('text') or "Sem texto")[:1000],
            'url': p.get('url', p.get('facebookUrl', '')),
            'timestamp': tratar_data(p),
            'image_url': p.get('displayUrl') or p.get('mediaUrl') or p.get('image') or ''
        }

        pop_calculada = calcular_popularidade(likes, comments)
        db_connection.upsert_social_real(pr_sql, fonte, rede, pop_calculada, 0)


def executar_tudo():
    """Main orchestration with Gatekeeper blocking."""
    print(f"\n--- RUN START: {datetime.now().strftime('%d/%m/%Y %H:%M')} ---")

    # Step 1: Gatekeeper - check pending checkpoints
    try:
        df_update = db_connection.get_posts_para_checkpoint()

        if not df_update.empty:
            print(f"BLOCKING: {len(df_update)} pending updates found.")
            print("Ensuring old data is complete before fetching new...")

            for rede in ['instagram', 'facebook']:
                urls = df_update[df_update['Plataforma'] == rede]['Link_Post'].tolist()[:50]
                if urls:
                    posts_revistos = extrair_posts_especificos(urls, rede)
                    processar_posts(posts_revistos, "Update", rede)

            print("Updates complete. Run ended to preserve dataset integrity.")
            return

        print("BD CLEAN: No posts waiting for 12h/24h/48h likes.")

    except Exception as e:
        print(f"Critical error in Checkpoints: {e}")
        return

    # Step 2: Discovery
    print("AUTHORIZED: Searching for new social media posts...")

    fontes = [
        {"user": "rtpnoticias", "nome": "RTP", "rede": "instagram"},
        {"user": "publico.pt", "nome": "Publico", "rede": "instagram"},
        {"user": "observador", "nome": "Observador", "rede": "instagram"},
        {"user": "rtpnoticias", "nome": "RTP", "rede": "facebook"},
        {"user": "publico", "nome": "Publico", "rede": "facebook"},
        {"user": "Observador", "nome": "Observador", "rede": "facebook"}
    ]

    for f in fontes:
        try:
            posts = extrair_instagram(f['user'], 5) if f['rede'] == "instagram" else extrair_facebook(f['user'], 5)
            processar_posts(posts, f['nome'], f['rede'])
            print(f"{f['nome']} ({f['rede']}) processed.")
        except Exception as e:
            print(f"Discovery error {f['nome']}: {e}")


if __name__ == "__main__":
    executar_tudo()
