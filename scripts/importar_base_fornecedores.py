from pathlib import Path
import sys

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.database import get_connection
from services.normalizer import normalizar_nome_fornecedor


BASE_DIR = Path(__file__).resolve().parents[1]
ARQUIVO_BASE_FORNECEDORES = BASE_DIR / "data" / "base_fornecedores.xlsx"


def importar_base_fornecedores() -> None:
    df = pd.read_excel(ARQUIVO_BASE_FORNECEDORES, dtype=str)
    df.columns = [str(c).strip().upper() for c in df.columns]

    df = df[["CODIGO", "FORNECEDOR"]].copy()
    df.rename(
        columns={
            "CODIGO": "codigo_fornecedor",
            "FORNECEDOR": "nome_oficial",
        },
        inplace=True,
    )

    df["codigo_fornecedor"] = df["codigo_fornecedor"].fillna("").astype(str).str.strip()
    df["nome_oficial"] = df["nome_oficial"].fillna("").astype(str).str.strip()
    df["nome_normalizado"] = df["nome_oficial"].apply(normalizar_nome_fornecedor)

    registros = [
        (
            row["codigo_fornecedor"] or None,
            row["nome_oficial"],
            row["nome_normalizado"],
        )
        for _, row in df.iterrows()
        if row["nome_oficial"]
    ]

    conn = get_connection()
    conn.execute("DELETE FROM fornecedores")
    conn.executemany(
        """
        INSERT INTO fornecedores (codigo_fornecedor, nome_oficial, nome_normalizado)
        VALUES (?, ?, ?)
        """,
        registros,
    )
    conn.commit()
    conn.close()

    print("Base de fornecedores importada com sucesso")


if __name__ == "__main__":
    importar_base_fornecedores()
