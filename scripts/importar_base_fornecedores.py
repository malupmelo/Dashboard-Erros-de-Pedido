import re
import unicodedata
from pathlib import Path

import pandas as pd

from core.database import get_connection


BASE_DIR = Path(__file__).resolve().parents[1]
ARQUIVO_BASE_FORNECEDORES = BASE_DIR / "data" / "base_fornecedores.xlsx"
TERMOS_REMOVER = {"ltda", "sa", "me", "eireli", "epp"}


def normalizar_nome_fornecedor(nome: str) -> str:
    texto = (nome or "").strip().lower()
    if not texto:
        return ""

    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = re.sub(r"[^a-z0-9\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()

    tokens = [t for t in texto.split(" ") if t and t not in TERMOS_REMOVER]
    return " ".join(tokens)


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
