#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
audit_categorization_detailed.py — Análise detalhada dos erros
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database import buscar_registros
from analytics import categorizar
from collections import Counter

registros = buscar_registros()

# Erros em "Outros"
erros_outros = [r["erro"] for r in registros if categorizar(r["erro"]) == ["Outros"]]

print("\n" + "=" * 80)
print("ANÁLISE DETALHADA DE ERROS EM 'OUTROS'")
print("=" * 80)
print(f"\nTotal: {len(erros_outros)} erros\n")

# Padrões encontrados
print("PADRÕES IDENTIFICADOS NOS ERROS EM 'OUTROS':\n")

# 1. Erros de PREÇO (FATURADO, VALOR, PC)
preco_keywords = ["faturado", "valor", "pc", "maior", "menor"]
erros_preco = [e for e in erros_outros if any(k in e.lower() for k in preco_keywords)]
print(f"1. Provavelmente PREÇO (contém 'faturado', 'valor', 'pc', 'maior', 'menor'):")
print(f"   {len(erros_preco)} erros")
print("   Exemplos:")
for e in erros_preco[:5]:
    print(f"     • {e[:70]}")

# 2. Erros de CÓDIGO/SERVIÇO
codigo_keywords = ["código", "code", "serviço", "servico"]
erros_codigo = [e for e in erros_outros if any(k in e.lower() for k in codigo_keywords)]
print(f"\n2. CÓDIGO/SERVIÇO (contém 'código', 'code', 'serviço'):")
print(f"   {len(erros_codigo)} erros")
print("   Exemplos:")
for e in erros_codigo[:5]:
    print(f"     • {e[:70]}")

# 3. Erros com IPI para redirecionamento
ipi_keywords = ["ipi", "4 %", "7 %", "12 %", "15 %", "%"]
erros_ipi = [e for e in erros_outros if any(k in e.lower() for k in ipi_keywords)]
print(f"\n3. Erros com IPI/ALÍQUOTA (contém 'ipi' ou percentuais):")
print(f"   {len(erros_ipi)} erros")
print("   Exemplos:")
for e in erros_ipi[:5]:
    print(f"     • {e[:70]}")

# 4. Erros de APROVAÇÃO/WORKFLOW
aprovacao_keywords = ["aprovação", "aprovaçao", "aprovado", "folha"]
erros_aprovacao = [e for e in erros_outros if any(k in e.lower() for k in aprovacao_keywords)]
print(f"\n4. APROVAÇÃO/WORKFLOW (contém 'aprovação', 'folha'):")
print(f"   {len(erros_aprovacao)} erros")
print("   Exemplos:")
for e in erros_aprovacao[:5]:
    print(f"     • {e[:70]}")

# 5. Erros de DUPLICAÇÃO/DIFERENTES
duplicacao_keywords = ["item", "alterar", "modificar", "diferente", "fechada"]
erros_duplicacao = [e for e in erros_outros if any(k in e.lower() for k in duplicacao_keywords)]
print(f"\n5. ITEM/ALTERAÇÃO (contém 'item', 'alterar', 'modificar', 'diferente'):")
print(f"   {len(erros_duplicacao)} erros")
print("   Exemplos:")
for e in erros_duplicacao[:5]:
    print(f"     • {e[:70]}")

# 6. Erros de EMPRESA/FORNECEDOR
empresa_keywords = ["vivix", "rodotransfer", "djr", "distribuicao", "distribuidora", "matriz", "goiana", "recife"]
erros_empresa = [e for e in erros_outros if any(k in e.lower() for k in empresa_keywords)]
print(f"\n6. EMPRESA/FORNECEDOR (contém nomes de empresas):")
print(f"   {len(erros_empresa)} erros")
print("   Exemplos:")
for e in erros_empresa[:5]:
    print(f"     • {e[:70]}")

# Erros sem categoria clara
sem_categoria_clara = set(erros_outros) - set(erros_preco) - set(erros_codigo) - set(erros_ipi) - set(erros_aprovacao) - set(erros_duplicacao) - set(erros_empresa)
print(f"\n7. SEM PADRÃO CLARO ({len(sem_categoria_clara)} erros):")
for e in list(sem_categoria_clara)[:10]:
    print(f"     • {e[:70]}")

# Resumo de melhorias sugeridas
print("\n" + "=" * 80)
print("SUGESTÕES DE MELHORIAS NAS PALAVRAS-CHAVE:")
print("=" * 80)
print("""
1. PREÇO:
   Adicionar: ["faturado", "valor", "pc", "maior", "menor", "unitário"]

2. Criar categoria NOVO: "Código/Serviço"
   Palavras-chave: ["código", "code", "serviço", "servico"]

3. Regras específicas de IPI:
    "ipi diferente do pedido/nota" -> "NCM"
    "alterar para x por causa do ipi" -> "IVA"

4. Criar categoria NOVO: "Aprovação"
   Palavras-chave: ["aprovação", "aprovaçao", "aprovado"]

5. FATURA FINAL (expandir):
   Adicionar: ["fechada", "item final"]
""")
