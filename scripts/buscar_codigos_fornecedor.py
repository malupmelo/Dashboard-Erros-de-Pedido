import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from core.database import get_connection

# Códigos extraídos da lista do usuário
codigos = [
    "1015717",
    "1009533",
    "300032489",
    "300033019",
    "300033254",
    "000550113-1",
    "1003039",
    "1006799",
    "1006976",
    "1010161",
    "1010239",
    "1015063",
    "1015788",
    "1016459",
    "1017802",
    "1018127",
    "1018225",
    "1018889",
    "1019427",
    "1019431",
    "1019481",
    "1019709",
    "1019721",
    "1672",
    "300027677",
    "300028048",
    "300028496",
    "300028774",
    "300029144",
    "300031349",
    "300031513",
    "300031671",
    "300031921",
    "300032230",
    "300032378",
    "300032533",
    "300032865",
    "300033051",
    "300033180",
    "300033458",
    "300033552",
    "300033598",
    "6899",
]

# Conectar ao banco
conn = get_connection()
cursor = conn.cursor()

# Resultado
encontrados = []
nao_encontrados = []

print(f"\nBuscando {len(codigos)} códigos na base de fornecedores...\n")
print("=" * 100)

for codigo in codigos:
    # Buscar por codigo_fornecedor
    cursor.execute("""
        SELECT codigo_fornecedor, nome_oficial, nome_normalizado 
        FROM fornecedores 
        WHERE codigo_fornecedor = ?
    """, (codigo,))
    
    resultado = cursor.fetchone()
    
    if resultado:
        encontrados.append((codigo, resultado[1], resultado[0]))
        print(f"✓ {codigo:15} → {resultado[1]}")
    else:
        nao_encontrados.append(codigo)
        print(f"✗ {codigo:15} → NÃO ENCONTRADO")

print("=" * 100)
print(f"\n📊 RESUMO:")
print(f"   ✓ Encontrados na base: {len(encontrados)}/{len(codigos)}")
print(f"   ✗ Não encontrados: {len(nao_encontrados)}/{len(codigos)}")

if nao_encontrados:
    print(f"\n❌ Códigos NÃO ENCONTRADOS na base:")
    for cod in nao_encontrados:
        print(f"   - {cod}")

conn.close()
