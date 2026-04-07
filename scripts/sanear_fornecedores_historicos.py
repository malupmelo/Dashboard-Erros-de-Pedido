import argparse
import os
import re
import sys
from collections import Counter

# Garante imports a partir da raiz do projeto quando executado via scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import get_connection
from services.fornecedor_service import buscar_fornecedor_por_codigo, buscar_fornecedor_por_nome
from services.importer import eh_codigo, _normalizar_fornecedor_texto


def resolver_fornecedor(fornecedor_valor: str) -> dict:
    original = (fornecedor_valor or "").strip()
    normalizado = _normalizar_fornecedor_texto(original)

    if eh_codigo(original):
        codigo_limpo = re.sub(r"\s+", "", original)
        encontrado = buscar_fornecedor_por_codigo(codigo_limpo)
        if encontrado:
            return {
                "fornecedor_original": original,
                "fornecedor_normalizado": normalizado,
                "fornecedor_canonico": encontrado["nome_oficial"],
                "codigo_fornecedor": encontrado["codigo_fornecedor"],
                "tipo_match_fornecedor": "codigo_exato",
            }
        return {
            "fornecedor_original": original,
            "fornecedor_normalizado": normalizado,
            "fornecedor_canonico": "FORNECEDOR NAO CADASTRADO",
            "codigo_fornecedor": codigo_limpo,
            "tipo_match_fornecedor": "codigo_nao_encontrado",
        }

    encontrado = buscar_fornecedor_por_nome(normalizado)
    if encontrado:
        return {
            "fornecedor_original": original,
            "fornecedor_normalizado": normalizado,
            "fornecedor_canonico": encontrado["nome_oficial"],
            "codigo_fornecedor": (encontrado.get("codigo_fornecedor") or "").strip(),
            "tipo_match_fornecedor": "nome_encontrado",
        }

    return {
        "fornecedor_original": original,
        "fornecedor_normalizado": normalizado,
        "fornecedor_canonico": original,
        "codigo_fornecedor": "",
        "tipo_match_fornecedor": "nome_nao_encontrado",
    }


def carregar_registros_erros() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, fornecedor FROM erros ORDER BY id ASC").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def atualizar_campos_fornecedor(atualizacoes: list[dict]) -> int:
    conn = get_connection()
    try:
        conn.executemany(
            """
            UPDATE erros
            SET
                fornecedor_original = ?,
                fornecedor_normalizado = ?,
                fornecedor_canonico = ?,
                codigo_fornecedor = ?,
                tipo_match_fornecedor = ?
            WHERE id = ?
            """,
            [
                (
                    item["fornecedor_original"],
                    item["fornecedor_normalizado"],
                    item["fornecedor_canonico"],
                    item["codigo_fornecedor"],
                    item["tipo_match_fornecedor"],
                    item["id"],
                )
                for item in atualizacoes
            ],
        )
        conn.commit()
        return conn.total_changes
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Saneia historico de fornecedores na tabela erros usando a logica atual (codigo ou nome)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Somente calcula e mostra a classificacao; nao grava no banco.",
    )
    args = parser.parse_args()

    registros = carregar_registros_erros()
    total = len(registros)

    atualizacoes = []
    tipos = Counter()

    for row in registros:
        resolvido = resolver_fornecedor(row.get("fornecedor", ""))
        tipos[resolvido["tipo_match_fornecedor"]] += 1
        resolvido["id"] = row["id"]
        atualizacoes.append(resolvido)

    print("Total de registros lidos:", total)
    print("codigo_exato:", tipos["codigo_exato"])
    print("codigo_nao_encontrado:", tipos["codigo_nao_encontrado"])
    print("nome_encontrado:", tipos["nome_encontrado"])
    print("nome_nao_encontrado:", tipos["nome_nao_encontrado"])

    if args.dry_run:
        print("Dry-run habilitado: nenhuma atualizacao foi gravada.")
        return 0

    alterados = atualizar_campos_fornecedor(atualizacoes)
    print("Registros atualizados:", alterados)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
