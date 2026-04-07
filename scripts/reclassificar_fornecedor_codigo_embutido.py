import argparse
import os
import re
import sys

# Garante imports a partir da raiz do projeto quando executado via scripts/
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.database import get_connection
from services.fornecedor_service import buscar_fornecedor_por_codigo


def extrair_codigo_inicial(valor: str) -> str:
    """Extrai apenas a sequencia numerica inicial do campo fornecedor."""
    texto = (valor or "").strip()
    match = re.match(r"^(\d+)", texto)
    if not match:
        return ""
    return match.group(1)


def buscar_candidatos_nome_nao_encontrado() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                id,
                fornecedor,
                fornecedor_original,
                fornecedor_canonico,
                codigo_fornecedor,
                tipo_match_fornecedor
            FROM erros
            WHERE tipo_match_fornecedor = 'nome_nao_encontrado'
            ORDER BY id ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def reclassificar_nome_nao_encontrado_por_codigo(limit: int = 10, dry_run: bool = False) -> dict:
    candidatos = buscar_candidatos_nome_nao_encontrado()
    atualizacoes = []
    exemplos = []

    for row in candidatos:
        fornecedor_original = (row.get("fornecedor_original") or row.get("fornecedor") or "").strip()
        codigo_extraido = extrair_codigo_inicial(fornecedor_original)
        if not codigo_extraido:
            continue

        encontrado = buscar_fornecedor_por_codigo(codigo_extraido)
        if not encontrado:
            continue

        antes = {
            "id": row["id"],
            "fornecedor_original": fornecedor_original,
            "fornecedor_canonico": row.get("fornecedor_canonico") or "",
            "codigo_fornecedor": row.get("codigo_fornecedor") or "",
            "tipo_match_fornecedor": row.get("tipo_match_fornecedor") or "",
        }
        depois = {
            "fornecedor_canonico": encontrado["nome_oficial"],
            "codigo_fornecedor": codigo_extraido,
            "tipo_match_fornecedor": "codigo_exato",
        }

        atualizacoes.append(
            {
                "id": row["id"],
                "fornecedor_canonico": depois["fornecedor_canonico"],
                "codigo_fornecedor": depois["codigo_fornecedor"],
                "tipo_match_fornecedor": depois["tipo_match_fornecedor"],
            }
        )

        if len(exemplos) < max(limit, 0):
            exemplos.append({"antes": antes, "depois": depois})

    alterados = 0
    if not dry_run and atualizacoes:
        conn = get_connection()
        try:
            conn.executemany(
                """
                UPDATE erros
                SET
                    fornecedor_canonico = ?,
                    codigo_fornecedor = ?,
                    tipo_match_fornecedor = ?
                WHERE id = ?
                  AND tipo_match_fornecedor = 'nome_nao_encontrado'
                """,
                [
                    (
                        item["fornecedor_canonico"],
                        item["codigo_fornecedor"],
                        item["tipo_match_fornecedor"],
                        item["id"],
                    )
                    for item in atualizacoes
                ],
            )
            conn.commit()
            alterados = conn.total_changes
        finally:
            conn.close()

    return {
        "total_nome_nao_encontrado": len(candidatos),
        "total_reclassificaveis": len(atualizacoes),
        "total_reclassificados": len(atualizacoes) if dry_run else alterados,
        "exemplos": exemplos,
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reclassifica registros nome_nao_encontrado quando fornecedor_original inicia com codigo numerico existente na base."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Somente simula a reclassificacao sem gravar no banco.",
    )
    parser.add_argument(
        "--exemplos",
        type=int,
        default=10,
        help="Quantidade de exemplos antes/depois para exibir no final.",
    )
    args = parser.parse_args()

    resultado = reclassificar_nome_nao_encontrado_por_codigo(
        limit=args.exemplos,
        dry_run=args.dry_run,
    )

    print("Total com tipo nome_nao_encontrado:", resultado["total_nome_nao_encontrado"])
    print("Total reclassificavel por codigo no inicio:", resultado["total_reclassificaveis"])
    if resultado["dry_run"]:
        print("Dry-run habilitado: nenhuma alteracao foi gravada.")
    print("Total reclassificado:", resultado["total_reclassificados"])

    if resultado["exemplos"]:
        print("\nExemplos antes/depois:")
        for item in resultado["exemplos"]:
            antes = item["antes"]
            depois = item["depois"]
            print(
                f"- id={antes['id']} | original='{antes['fornecedor_original']}' "
                f"| antes: tipo={antes['tipo_match_fornecedor']}, codigo='{antes['codigo_fornecedor']}', canonico='{antes['fornecedor_canonico']}' "
                f"| depois: tipo={depois['tipo_match_fornecedor']}, codigo='{depois['codigo_fornecedor']}', canonico='{depois['fornecedor_canonico']}'"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
