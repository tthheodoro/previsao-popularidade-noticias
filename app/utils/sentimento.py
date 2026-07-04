"""
Sentiment Analysis — versão unificada.
---------------------------------------
Análise de sentimento baseada em léxico com tratamento de expressões compostas.
Usada tanto no treino (dados_portugal.py) como em produção (servidor.py).
"""

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
    """Calcula a carga emocional utilizando análise sintática e de exceções."""
    if not txt:
        return 0
    t = txt.lower()

    pontuacao = 0

    # PASSO 1: Procurar Expressões Compostas (Têm prioridade máxima)
    for exp in EXCECOES_NEGATIVAS:
        if exp in t:
            pontuacao -= 2
            t = t.replace(exp, "")  # Remove da frase para não ler as palavras soltas depois

    for exp in EXCECOES_POSITIVAS:
        if exp in t:
            pontuacao += 2
            t = t.replace(exp, "")

    # PASSO 2: Procurar Palavras Soltas (Valem 1 ponto)
    pontuacao += sum(1 for p in PAL_POS if p in t)
    pontuacao -= sum(1 for n in PAL_NEG if n in t)

    # PASSO 3: Limitar o score para não criar valores absurdos que confundam a IA
    if pontuacao > 5:
        pontuacao = 5
    if pontuacao < -5:
        pontuacao = -5

    return pontuacao
