"""
Script de auditoria da importação de dados.
Uso: python scripts/audit_import.py
Execute a partir da raiz do projeto.
"""
import os
import sys

# Adiciona a raiz do projeto ao path para importar os módulos
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
import services.importer as importer
from core.database import init_db, get_connection

# ensure database initialized
init_db()

print("=> Pasta data:", importer.PASTA_DATA)
files = sorted([f for f in os.listdir(importer.PASTA_DATA) if f.lower().endswith('.xlsx')])
print(f"Arquivos encontrados: {len(files)}")
for f in files:
    path = os.path.join(importer.PASTA_DATA, f)
    print("\n--- Processando", f)
    try:
        df = importer.processar_arquivo(path)
        total = len(df)
        print(f"Linhas válidas (após dropna/format): {total}")
        raw = df.copy()
        required = list(importer.COLUNAS_OBRIGATORIAS)
        missing = raw[required].isnull().any(axis=1).sum()
        print(f"Linhas com colunas obrigatórias vazias (deve ser 0): {missing}")
    except Exception as e:
        print(f"Erro processando {f}: {e}")
        continue

print("\nInserindo no banco usando importar_pasta_data()")
imported_count = importer.importar_pasta_data()
print("Registros importados retornado:", imported_count)

# consultar banco
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM erros")
count_db = cur.fetchone()[0]
print("Total de registros no banco:", count_db)

cur.execute("SELECT arquivo, registros FROM importacoes")
print("Importacoes gravadas:")
for row in cur.fetchall():
    print(row)

conn.close()
