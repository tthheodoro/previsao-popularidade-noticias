"""Testes manuais da função de sentimento unificada."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.sentimento import analisar_sentimento

tests = [
    ("O desemprego cai em Portugal",              "excecao positiva"),
    ("A crise cresce no pais",                     "excecao negativa"),
    ("Governo anuncia sucesso economico",          "frase positiva"),
    ("Problema grave na saude publica",            "frase negativa"),
    ("O tempo esta hoje",                          "frase neutra"),
    ("",                                           "string vazia"),
    ("Desemprego sobe para niveis recordes",       "excecao negativa 2"),
    ("Inflacao desce pela primeira vez",           "excecao positiva 2"),
]

print("=== Testes de Sentimento Unificado ===\n")

for texto, desc in tests:
    resultado = analisar_sentimento(texto)
    sinal = "+" if resultado > 0 else ("-" if resultado < 0 else "=")
    print(f"  [{sinal}] {resultado:+d}  |  {desc}")
    print(f"      \"{texto}\"")
    print()

# Confirmar que servidor.py importa a mesma função
from app.servidor import analisar_sentimento as srv_func
test_unified = analisar_sentimento("O desemprego cai em Portugal")
test_server = srv_func("O desemprego cai em Portugal")
print(f"=== Consistencia ===")
print(f"  sentimento.py: {test_unified}")
print(f"  servidor.py:   {test_server}")
print(f"  Iguais: {test_unified == test_server}")
