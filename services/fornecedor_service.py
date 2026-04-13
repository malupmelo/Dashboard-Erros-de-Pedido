from rapidfuzz import fuzz, process

from core.database import get_connection


def buscar_fornecedor_por_codigo(codigo_fornecedor: str, conn=None) -> dict | None:
    """Busca fornecedor oficial na base mestre pelo codigo."""
    codigo = (codigo_fornecedor or "").strip()
    if not codigo:
        return None

    conexao = conn or get_connection()
    fechar_conn = conn is None
    row = conexao.execute(
        """
        SELECT codigo_fornecedor, nome_oficial, nome_normalizado
        FROM fornecedores
        WHERE codigo_fornecedor = ?
        LIMIT 1
        """,
        (codigo,),
    ).fetchone()
    if fechar_conn:
        conexao.close()

    if not row:
        return None

    return {
        "codigo_fornecedor": row["codigo_fornecedor"],
        "nome_oficial": row["nome_oficial"],
        "nome_normalizado": row["nome_normalizado"],
    }


def buscar_fornecedor_por_nome(nome_normalizado: str, conn=None) -> dict | None:
    """Busca fornecedor oficial na base mestre pelo nome normalizado."""
    nome = (nome_normalizado or "").strip()
    if not nome:
        return None

    conexao = conn or get_connection()
    fechar_conn = conn is None
    row = conexao.execute(
        """
        SELECT codigo_fornecedor, nome_oficial, nome_normalizado
        FROM fornecedores
        WHERE nome_normalizado = ?
        LIMIT 1
        """,
        (nome,),
    ).fetchone()
    if fechar_conn:
        conexao.close()

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


def buscar_fornecedor_por_alias(alias_normalizado: str, conn=None):
    """Busca fornecedor pela tabela de aliases manuais."""
    alias = (alias_normalizado or "").strip()
    if not alias:
        return None

    conexao = conn or get_connection()
    fechar_conn = conn is None
    row = conexao.execute(
        """
        SELECT f.codigo_fornecedor, f.nome_oficial, f.nome_normalizado
        FROM fornecedor_aliases a
        JOIN fornecedores f ON f.codigo_fornecedor = a.codigo_fornecedor
        WHERE a.alias_normalizado = ?
        LIMIT 1
        """,
        (alias,),
    ).fetchone()
    if fechar_conn:
        conexao.close()

    if not row:
        return None

    return {
        "codigo_fornecedor": row["codigo_fornecedor"],
        "nome_oficial": row["nome_oficial"],
        "nome_normalizado": row["nome_normalizado"],
    }


def buscar_fornecedor_fuzzy(nome_normalizado: str, threshold: int = 82, conn=None):
    """Fuzzy matching contra todos os nome_normalizado da tabela fornecedores.

    Usa rapidfuzz.fuzz.token_sort_ratio (tolerante à ordem das palavras).
    Retorna tupla: (dict_fornecedor, score_int, "fuzzy_match") ou (None, None, "nome_nao_encontrado")
    """
    nome = (nome_normalizado or "").strip()
    if not nome:
        return None, None, "nome_nao_encontrado"

    conexao = conn or get_connection()
    fechar_conn = conn is None
    rows = conexao.execute(
        """
        SELECT codigo_fornecedor, nome_oficial, nome_normalizado
        FROM fornecedores
        WHERE nome_normalizado IS NOT NULL AND nome_normalizado <> ''
        """
    ).fetchall()

    if not rows:
        if fechar_conn:
            conexao.close()
        return None, None, "nome_nao_encontrado"

    candidatos = [row["nome_normalizado"] for row in rows]
    melhor = process.extractOne(nome, candidatos, scorer=fuzz.token_sort_ratio)

    if fechar_conn:
        conexao.close()

    if not melhor:
        return None, None, "nome_nao_encontrado"

    _, score, indice = melhor
    if score < threshold:
        return None, None, "nome_nao_encontrado"

    row = rows[indice]
    score_int = int(round(score))
    return (
        {
            "codigo_fornecedor": row["codigo_fornecedor"],
            "nome_oficial": row["nome_oficial"],
            "nome_normalizado": row["nome_normalizado"],
        },
        score_int,
        "fuzzy_match",
    )
