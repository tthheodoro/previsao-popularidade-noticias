---
title: AI Popularity Predictor
emoji: 📊
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---

# AI Popularity Predictor

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)](https://scikit-learn.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

Sistema preditivo de popularidade para conteúdo digital, utilizando machine learning para antecipar o engajamento de notícias e publicações em redes sociais.

[![Deploy](https://img.shields.io/badge/Deploy-Hugging%20Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/spaces)

---

## Funcionalidades

- **Previsão de Notícias** - Análise de título, descrição e categoria para estimar popularidade
- **Previsão de Redes Sociais** - Análise de métricas (likes, seguidores, comentários) + processamento de imagens (deteção de rostos, luminosidade)
- **Calibração Dinâmica** - Ajuste automático baseado no tamanho da audiência
- **Active Learning** - Feedback do utilizador para melhorar o modelo recursivamente
- **Sistema de Autenticação** - Registo, login e gestão de sessões com JWT
- **Dashboard de Histórico** - Visualização de previsões anteriores e feedback

---

## Arquitetura

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend   │────▶│  API Flask   │────▶│   SQLite    │
│  HTML/CSS/JS │     │   Backend    │     │  Database   │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  ML Models   │
                    │ Random Forest│
                    └──────────────┘
```

---

## Stack Tecnológica

| Camada | Tecnologias |
|--------|-------------|
| **Backend** | Python 3.11, Flask 3.0, SQLite |
| **Machine Learning** | Scikit-Learn (Random Forest), OpenCV |
| **Autenticação** | JWT, bcrypt |
| **Scraping** | Apify SDK, BeautifulSoup |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Deploy** | Docker, Hugging Face Spaces |
| **CI/CD** | GitHub Actions |

---

## Estrutura do Projeto

```
├── app/                    # Código principal
│   ├── servidor.py         # API Flask
│   ├── db_connection.py    # Base de dados
│   ├── scraper/            # Scraping redes sociais
│   ├── analysis/           # Recolha RSS
│   └── utils/              # Processamento imagens
├── models/                 # Modelos ML
├── scripts/                # Scripts utilitários
├── static/                 # CSS + JavaScript
├── templates/              # HTML templates
├── data/                   # Base de dados
└── output/                 # Gráficos gerados
```

---

## Setup Local

**Pré-requisitos:** Python 3.11+, pip

```bash
# 1. Clonar repositório
git clone https://github.com/tthheodor/previsao-popularidade.git
cd previsao-popularidade

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Configurar variáveis de ambiente
echo "SECRET_KEY=sua_chave_secreta_aqui" > .env

# 4. Iniciar servidor
python -m app.servidor
```

O servidor inicia em `http://127.0.0.1:7860`

---

## API Endpoints

| Método | Rota | Descrição | Auth |
|--------|------|-----------|------|
| GET | `/` | Dashboard principal | Não |
| GET | `/login-page` | Página de login | Não |
| GET | `/health` | Health check | Não |
| POST | `/api/registar` | Registar utilizador | Não |
| POST | `/api/login` | Iniciar sessão | Não |
| POST | `/prever` | Previsão de notícia | Sim |
| POST | `/prever_social` | Previsão de rede social | Sim |
| POST | `/feedback` | Submeter feedback | Sim |
| GET | `/api/historico` | Obter histórico | Sim |
| GET | `/api/perfil` | Obter perfil | Sim |

---

## Models

O sistema utiliza dois modelos Random Forest:

- **modelo_noticias.pkl** - Prevê popularidade baseada em metadados textuais (título, descrição, categoria, sentimento)
- **modelo_social.pkl** - Prevê popularidade baseada em métricas de engajamento e características visuais

Para retreinar com dados reais:

```bash
python models/treinar_noticias.py
python models/treinar_social.py
```

---

## Deploy

O projeto está containerizado com Docker para deploy automático via GitHub Actions para Hugging Face Spaces.

---

## Autores

**Desenvolvido por:**

- **Tiago Miguel Caetano Teodoro** - [GitHub](https://github.com/tthheodoro/)
- **Rodrigo Henriques** - [GitHub](https://github.com/01RodrigoHenriques)
- **João Pedro Nunes Esteves** - [GitHub](https://github.com/jpneves-estev)

**Orientação Científica:**

- Prof. Doutor Eduardo Sabina dos Santos Valente

---

## Instituição

**Escola Superior de Tecnologia**
Instituto Politécnico de Castelo Branco
2025/2026

---

## Licença

Este projeto é parte de um Trabalho Final de Licenciatura.
