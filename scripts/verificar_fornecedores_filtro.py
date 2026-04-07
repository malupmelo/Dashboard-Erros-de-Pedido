import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from web.routes import _listar_fornecedores_canonicos

ALVOS = [
    "DM SERVICOS LTDA",
    "C.A.C PARK ESTACIONAMENTOS LTDA",
    "SNOWFLAKE BRAZIL LTDA",
]

opcoes = _listar_fornecedores_canonicos()
labels = {o["label"] for o in opcoes}
values = {o["value"] for o in opcoes}

print(f"Total de opções no filtro: {len(opcoes)}")
print("\nVerificação dos alvos:")
for alvo in ALVOS:
    encontrado_label = alvo in labels
    encontrado_value = alvo in values
    print(f"- {alvo}: label={encontrado_label}, value={encontrado_value}")

print("\nPrimeiras 30 opções do filtro:")
for item in opcoes[:30]:
    print(f"{item['label']}")
