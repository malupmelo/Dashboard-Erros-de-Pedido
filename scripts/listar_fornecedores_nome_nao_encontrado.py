import argparse
import os
import sqlite3
from pathlib import Path


def _default_db_path() -> Path:
    return Path(__file__).resolve().parents[1] / "erros_pedido.db"


def _query_rows(conn: sqlite3.Connection, limit: int | None):
    sql = """
    SELECT
        trim(
            coalesce(nullif(fornecedor_original, ''), nullif(fornecedor_canonico, ''), nullif(fornecedor, ''))
        ) AS fornecedor_nome,
        count(*) AS ocorrencias
    FROM erros
    WHERE tipo_match_fornecedor = 'nome_nao_encontrado'
      AND trim(coalesce(fornecedor_original, fornecedor_canonico, fornecedor, '')) <> ''
      AND instr(lower(coalesce(fornecedor_original, fornecedor_canonico, fornecedor, '')), '@') = 0
      AND instr(lower(coalesce(fornecedor_original, fornecedor_canonico, fornecedor, '')), 'www.') = 0
      AND instr(lower(coalesce(fornecedor_original, fornecedor_canonico, fornecedor, '')), 'cid:') = 0
    GROUP BY fornecedor_nome
    ORDER BY ocorrencias DESC, fornecedor_nome ASC
    """

    if limit and limit > 0:
        sql += "\nLIMIT ?"
        return conn.execute(sql, (limit,)).fetchall()

    return conn.execute(sql).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lista fornecedores com tipo_match_fornecedor=nome_nao_encontrado, agrupados por frequência."
    )
    parser.add_argument(
        "--db",
        default=str(_default_db_path()),
        help="Caminho do arquivo SQLite (default: erros_pedido.db na raiz do projeto).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Quantidade máxima de linhas no resultado (0 = sem limite).",
    )
    args = parser.parse_args()

    db_path = os.path.abspath(args.db)
    if not os.path.exists(db_path):
        print(f"Banco não encontrado: {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = _query_rows(conn, args.limit)
    finally:
        conn.close()

    if not rows:
        print("Nenhum fornecedor com nome_nao_encontrado encontrado após filtros.")
        return 0

    print("fornecedor_nome;ocorrencias")
    for row in rows:
        print(f"{row['fornecedor_nome']};{row['ocorrencias']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
