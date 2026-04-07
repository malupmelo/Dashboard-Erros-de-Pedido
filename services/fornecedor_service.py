from core.database import get_connection


def buscar_fornecedor_por_codigo(codigo_fornecedor: str) -> dict | None:
    """Busca fornecedor oficial na base mestre pelo codigo."""
    codigo = (codigo_fornecedor or "").strip()
    if not codigo:
        return None

    conn = get_connection()
    row = conn.execute(
        """
        SELECT codigo_fornecedor, nome_oficial, nome_normalizado
        FROM fornecedores
        WHERE codigo_fornecedor = ?
        LIMIT 1
        """,
        (codigo,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    return {
        "codigo_fornecedor": row["codigo_fornecedor"],
        "nome_oficial": row["nome_oficial"],
        "nome_normalizado": row["nome_normalizado"],
    }


def buscar_fornecedor_por_nome(nome_normalizado: str) -> dict | None:
    """Busca fornecedor oficial na base mestre pelo nome normalizado."""
    nome = (nome_normalizado or "").strip()
    if not nome:
        return None

    conn = get_connection()
    row = conn.execute(
        """
        SELECT codigo_fornecedor, nome_oficial, nome_normalizado
        FROM fornecedores
        WHERE nome_normalizado = ?
        LIMIT 1
        """,
        (nome,),
    ).fetchone()
    conn.close()

    if not row:
        return None

    return {
        "codigo_fornecedor": row["codigo_fornecedor"],
        "nome_oficial": row["nome_oficial"],
        "nome_normalizado": row["nome_normalizado"],
    }


def buscar_fornecedor_por_nome_normalizado(nome_normalizado: str) -> dict | None:
    """Compatibilidade: alias para busca por nome normalizado."""
    return buscar_fornecedor_por_nome(nome_normalizado)
