import os
import re
import sqlite3
from collections import Counter


DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "erros_pedido.db")


def pct(parte: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return (parte / total) * 100.0


def fornecedor_texto(row: sqlite3.Row) -> str:
    return (row["fornecedor_original"] or row["fornecedor_canonico"] or row["fornecedor"] or "").strip()


def main() -> int:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total_registros = conn.execute("SELECT COUNT(*) AS c FROM erros").fetchone()["c"]

    rows_tipo = conn.execute(
        """
        SELECT COALESCE(tipo_match_fornecedor, 'sem_tipo') AS tipo, COUNT(*) AS total
        FROM erros
        GROUP BY COALESCE(tipo_match_fornecedor, 'sem_tipo')
        ORDER BY total DESC
        """
    ).fetchall()
    por_tipo = {r["tipo"]: r["total"] for r in rows_tipo}

    codigo_exato = por_tipo.get("codigo_exato", 0)
    nome_encontrado = por_tipo.get("nome_encontrado", 0)
    codigo_nao_encontrado = por_tipo.get("codigo_nao_encontrado", 0)
    nome_nao_encontrado = por_tipo.get("nome_nao_encontrado", 0)
    sem_tipo = por_tipo.get("sem_tipo", 0)

    mapeados = codigo_exato + nome_encontrado
    pendentes = codigo_nao_encontrado + nome_nao_encontrado + sem_tipo

    fornecedores_confiaveis_distintos = conn.execute(
        """
        SELECT COUNT(DISTINCT TRIM(fornecedor_canonico)) AS c
        FROM erros
        WHERE tipo_match_fornecedor IN ('codigo_exato', 'nome_encontrado')
          AND fornecedor_canonico IS NOT NULL
          AND TRIM(fornecedor_canonico) <> ''
        """
    ).fetchone()["c"]

    codigos_nao_cadastrados_distintos = conn.execute(
        """
        SELECT COUNT(DISTINCT TRIM(codigo_fornecedor)) AS c
        FROM erros
        WHERE tipo_match_fornecedor = 'codigo_nao_encontrado'
          AND codigo_fornecedor IS NOT NULL
          AND TRIM(codigo_fornecedor) <> ''
        """
    ).fetchone()["c"]

    top_codigos_nao_cadastrados = conn.execute(
        """
        SELECT TRIM(codigo_fornecedor) AS codigo, COUNT(*) AS total
        FROM erros
        WHERE tipo_match_fornecedor = 'codigo_nao_encontrado'
          AND codigo_fornecedor IS NOT NULL
          AND TRIM(codigo_fornecedor) <> ''
        GROUP BY TRIM(codigo_fornecedor)
        ORDER BY total DESC, codigo ASC
        LIMIT 10
        """
    ).fetchall()

    rows_nome_nao = conn.execute(
        """
        SELECT fornecedor, fornecedor_original, fornecedor_canonico
        FROM erros
        WHERE tipo_match_fornecedor = 'nome_nao_encontrado'
        """
    ).fetchall()

    nomes_distintos_counter = Counter()
    nome_nao_com_codigo_inicio = 0
    nome_nao_com_codigo_inicio_cadastrado = 0
    nome_nao_com_email = 0
    nome_nao_com_www_ou_cid = 0

    for row in rows_nome_nao:
        texto = fornecedor_texto(row)
        if texto:
            nomes_distintos_counter[texto] += 1

        t_low = texto.lower()
        if "@" in texto:
            nome_nao_com_email += 1
        if "www." in t_low or "cid:" in t_low:
            nome_nao_com_www_ou_cid += 1

        m = re.match(r"^(\d+)", texto)
        if not m:
            continue

        nome_nao_com_codigo_inicio += 1
        codigo = m.group(1)
        existe = conn.execute(
            "SELECT 1 FROM fornecedores WHERE codigo_fornecedor = ? LIMIT 1",
            (codigo,),
        ).fetchone()
        if existe:
            nome_nao_com_codigo_inicio_cadastrado += 1

    nomes_nao_cadastrados_distintos = len(nomes_distintos_counter)
    top_nomes_nao_cadastrados = nomes_distintos_counter.most_common(15)

    conn.close()

    print("ANALISE QUANTITATIVA - MAPEAMENTO DE FORNECEDORES")
    print("=" * 72)
    print(f"Total de registros em erros: {total_registros}")
    print()

    print("1) Cobertura de mapeamento")
    print(f"- Mapeados (codigo_exato + nome_encontrado): {mapeados} ({pct(mapeados, total_registros):.2f}%)")
    print(f"  - codigo_exato: {codigo_exato} ({pct(codigo_exato, total_registros):.2f}%)")
    print(f"  - nome_encontrado: {nome_encontrado} ({pct(nome_encontrado, total_registros):.2f}%)")
    print(f"- Pendentes (codigo_nao_encontrado + nome_nao_encontrado + sem_tipo): {pendentes} ({pct(pendentes, total_registros):.2f}%)")
    print(f"  - codigo_nao_encontrado: {codigo_nao_encontrado} ({pct(codigo_nao_encontrado, total_registros):.2f}%)")
    print(f"  - nome_nao_encontrado: {nome_nao_encontrado} ({pct(nome_nao_encontrado, total_registros):.2f}%)")
    print(f"  - sem_tipo: {sem_tipo} ({pct(sem_tipo, total_registros):.2f}%)")
    print()

    print("2) Cobertura de fornecedores confiaveis")
    print(f"- Fornecedores canonicos distintos (confiaveis): {fornecedores_confiaveis_distintos}")
    print()

    print("3) Parametrizacao de codigos nao cadastrados")
    print(f"- Registros com codigo_nao_encontrado: {codigo_nao_encontrado}")
    print(f"- Codigos nao cadastrados distintos: {codigos_nao_cadastrados_distintos}")
    print("- Top codigos nao cadastrados (codigo;ocorrencias):")
    if top_codigos_nao_cadastrados:
        for r in top_codigos_nao_cadastrados:
            print(f"  {r['codigo']};{r['total']}")
    else:
        print("  (nenhum)")
    print()

    print("4) Parametrizacao de nomes nao cadastrados")
    print(f"- Registros com nome_nao_encontrado: {nome_nao_encontrado}")
    print(f"- Nomes nao cadastrados distintos: {nomes_nao_cadastrados_distintos}")
    print(f"- Nome_nao_encontrado com codigo no inicio: {nome_nao_com_codigo_inicio} ({pct(nome_nao_com_codigo_inicio, nome_nao_encontrado):.2f}% da fila de nomes)")
    print(f"- Destes, com codigo existente na base mestre: {nome_nao_com_codigo_inicio_cadastrado}")
    print(f"- Com ruido de email (@): {nome_nao_com_email}")
    print(f"- Com ruido de www/cid: {nome_nao_com_www_ou_cid}")
    print("- Top nomes nao cadastrados (nome;ocorrencias):")
    if top_nomes_nao_cadastrados:
        for nome, total in top_nomes_nao_cadastrados:
            print(f"  {nome};{total}")
    else:
        print("  (nenhum)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
