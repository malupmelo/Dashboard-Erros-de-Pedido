# ─────────────────────────────────────────────
# database.py — Operações com o banco de dados
# ─────────────────────────────────────────────

import sqlite3
from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS erros (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            nf           TEXT,
            fornecedor   TEXT,
            pedido       TEXT,
            erro         TEXT,
            data         TEXT,
            comprador    TEXT,
            assunto      TEXT,
            remetente    TEXT,
            importado_em TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS importacoes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            arquivo      TEXT,
            registros    INTEGER,
            importado_em TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


def salvar_registros(registros: list[dict], nome_arquivo: str):
    """Salva registros no banco garantindo unicidade por NF + PEDIDO."""
    conn = get_connection()
    
    # 1) Limpa duplicidades históricas que já existirem no banco
    conn.execute(
        """
        DELETE FROM erros
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM erros
            GROUP BY nf, pedido
        )
        """
    )

    # 2) Remove duplicidades dentro da própria importação (mantém a primeira ocorrência)
    registros_unicos = {}
    for r in registros:
        chave = (r["NF"], r["PEDIDO"])
        if chave not in registros_unicos:
            registros_unicos[chave] = r

    # 3) Para cada chave importada, remove o existente e insere somente 1 registro
    for r in registros_unicos.values():
        conn.execute(
            "DELETE FROM erros WHERE nf=? AND pedido=?",
            (r["NF"], r["PEDIDO"])
        )
    for r in registros_unicos.values():
        conn.execute(
            "INSERT INTO erros (nf, fornecedor, pedido, erro, data, comprador, assunto, remetente) VALUES (?,?,?,?,?,?,?,?)",
            (r["NF"], r["FORNECEDOR"], r["PEDIDO"], r["ERRO"], r["DATA"], r["COMPRADOR"], r["ASSUNTO"], r["REMETENTE"])
        )

    # 4) Salvaguarda final: garante unicidade no estado final da tabela
    conn.execute(
        """
        DELETE FROM erros
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM erros
            GROUP BY nf, pedido
        )
        """
    )

    conn.execute(
        "INSERT INTO importacoes (arquivo, registros) VALUES (?,?)",
        (nome_arquivo, len(registros_unicos))
    )
    conn.commit()
    conn.close()


def buscar_registros():
    """Retorna todos os registros ordenados por data."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM erros ORDER BY data ASC, id ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def buscar_ultima_importacao():
    """Retorna informações da última importação."""
    conn = get_connection()
    row = conn.execute(
        "SELECT importado_em, registros FROM importacoes ORDER BY id DESC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def contar_registros():
    """Retorna total de registros no banco."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM erros").fetchone()[0]
    conn.close()
    return total
