#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
audit_categorization.py — Auditoria de categorização de erros
Analisa a categorização atual e identifica problemas
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.database import buscar_registros
from services.analytics import categorizar
from collections import Counter

# Buscar todos os registros
registros = buscar_registros()
total = len(registros)

print("=" * 80)
print("AUDITORIA DE CATEGORIZAÇÃO DE ERROS")
print("=" * 80)
print(f"\nTotal de registros: {total}\n")

# Contador de categorias
cat_counter = Counter()
for r in registros:
    cats = categorizar(r["erro"])
    for cat in cats:
        cat_counter[cat] += 1

print("DISTRIBUIÇÃO ATUAL POR CATEGORIA:")
print("-" * 80)
for cat, count in sorted(cat_counter.items(), key=lambda x: -x[1]):
    pct = (count / total * 100) if total > 0 else 0
    print(f"  {cat:30s} {count:4d} ({pct:5.1f}%)")

# Verificar erros contendo "iva"
print("\n" + "=" * 80)
print("AUDITORIA DE IVA:")
print("=" * 80)
erros_com_iva_lower = [r for r in registros if "iva" in r["erro"].lower()]
print(f"\nErros contendo 'iva' (case-insensitive): {len(erros_com_iva_lower)}")

# Ver quais desses NÃO estão sendo categorizados como IVA
erros_iva_nao_categorizados = []
for r in erros_com_iva_lower:
    cats = categorizar(r["erro"])
    if "IVA" not in cats:
        erros_iva_nao_categorizados.append((r["erro"], cats))

if erros_iva_nao_categorizados:
    print(f"\n[!] {len(erros_iva_nao_categorizados)} erros com 'iva' que NAO foram categorizados como IVA:")
    for erro, cats in erros_iva_nao_categorizados[:10]:
        print(f"  - ERRO: {erro[:70]}")
        print(f"    CATEGORIAS ATRIBUIDAS: {cats}")
        print()
else:
    print("\n[OK] Todos os erros com 'iva' foram categorizados como IVA")

# Amostra de erros classificados como "Outros"
print("\n" + "=" * 80)
print("AMOSTRA DE ERROS CLASSIFICADOS COMO 'OUTROS':")
print("=" * 80)
erros_outros = [(r["erro"], categorizar(r["erro"])) for r in registros if categorizar(r["erro"]) == ["Outros"]]
print(f"\nTotal de erros em 'Outros': {len(erros_outros)} ({len(erros_outros)/total*100:.1f}%)")
print("\nPrimeiros 30 exemplos:")
for i, (erro, cats) in enumerate(erros_outros[:30], 1):
    print(f"  {i:2d}. {erro[:75]}")

# Análise de termos frequentes em cada categoria
print("\n" + "=" * 80)
print("ANÁLISE DE PALAVRAS-CHAVE POR CATEGORIA:")
print("=" * 80)
from core.config import CATEGORIAS
for cat_nome, cat_keywords in CATEGORIAS:
    print(f"\n{cat_nome}:")
    print(f"  Palavras-chave: {cat_keywords}")
    count = cat_counter.get(cat_nome, 0)
    print(f"  Total: {count}")
