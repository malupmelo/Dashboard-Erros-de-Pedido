# ─────────────────────────────────────────────
# database.py — Operações com o banco de dados
# ─────────────────────────────────────────────

import sqlite3
from datetime import datetime
from core.config import DB_PATH


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

    # Migração incremental: garante colunas novas em bases antigas.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(erros)").fetchall()}
    if "comprador_original" not in cols:
        conn.execute("ALTER TABLE erros ADD COLUMN comprador_original TEXT")
    if "comprador_limpo" not in cols:
        conn.execute("ALTER TABLE erros ADD COLUMN comprador_limpo TEXT")
    if "comprador_normalizado" not in cols:
        conn.execute("ALTER TABLE erros ADD COLUMN comprador_normalizado TEXT")
    if "comprador_canonico" not in cols:
        conn.execute("ALTER TABLE erros ADD COLUMN comprador_canonico TEXT")

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
    agora_local = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
            (
                "INSERT INTO erros "
                "(nf, fornecedor, pedido, erro, data, comprador, assunto, remetente, importado_em, "
                "comprador_original, comprador_limpo, comprador_normalizado, comprador_canonico) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
            ),
            (
                r["NF"],
                r["FORNECEDOR"],
                r["PEDIDO"],
                r["ERRO"],
                r["DATA"],
                r["COMPRADOR"],
                r["ASSUNTO"],
                r["REMETENTE"],
                agora_local,
                r.get("COMPRADOR_ORIGINAL", ""),
                r.get("COMPRADOR_LIMPO", ""),
                r.get("COMPRADOR_NORMALIZADO", ""),
                r.get("COMPRADOR_CANONICO", ""),
            )
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
        "INSERT INTO importacoes (arquivo, registros, importado_em) VALUES (?,?,?)",
        (nome_arquivo, len(registros_unicos), agora_local)
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
