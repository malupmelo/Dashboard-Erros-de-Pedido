from pathlib import Path
import sys


# Permite execucao standalone: python scripts/sugerir_aliases.py
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.database import get_connection
from services.fornecedor_service import buscar_fornecedor_fuzzy, buscar_fornecedor_por_codigo


def coletar_candidatos(conn):
    """Lista aliases normalizados sem match e ainda nao cadastrados em fornecedor_aliases."""
    rows = conn.execute(
        """
        SELECT DISTINCT e.fornecedor_normalizado AS alias_normalizado
        FROM erros e
        LEFT JOIN fornecedor_aliases a
            ON a.alias_normalizado = e.fornecedor_normalizado
        WHERE e.tipo_match_fornecedor = 'nome_nao_encontrado'
          AND e.fornecedor_normalizado IS NOT NULL
          AND TRIM(e.fornecedor_normalizado) <> ''
          AND a.alias_normalizado IS NULL
        ORDER BY e.fornecedor_normalizado
        """
    ).fetchall()
    return [row["alias_normalizado"] for row in rows]


def salvar_alias(conn, alias_normalizado, codigo_fornecedor, origem):
    """Salva alias com INSERT OR IGNORE. Retorna True se inseriu, False se ja existia."""
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO fornecedor_aliases (alias_normalizado, codigo_fornecedor, origem)
        VALUES (?, ?, ?)
        """,
        (alias_normalizado, codigo_fornecedor, origem),
    )
    conn.commit()
    return cur.rowcount > 0


def ler_acao_usuario():
    while True:
        acao = input("Escolha [1/2/3/Q]: ").strip().upper()
        if acao in {"1", "2", "3", "Q"}:
            return acao
        print("Opcao invalida. Use 1, 2, 3 ou Q.")


def processar_candidatos(conn, candidatos, threshold=70):
    analisados = 0
    salvos = 0
    pulados = 0
    sem_sugestao = []
    encerrar = False

    for alias_normalizado in candidatos:
        analisados += 1
        fornecedor, score, _ = buscar_fornecedor_fuzzy(alias_normalizado, threshold=threshold, conn=conn)

        if not fornecedor:
            sem_sugestao.append(alias_normalizado)
            pulados += 1
            continue

        while True:
            print("\n" + "-" * 45)
            print(f'ENTRADA:  "{alias_normalizado}"')
            print(
                f'SUGESTAO: "{fornecedor["nome_oficial"]}" '
                f'(codigo: {fornecedor["codigo_fornecedor"]}, score: {score})'
            )
            print("\n[1] Confirmar e salvar alias")
            print("[2] Pular")
            print("[3] Digitar codigo manualmente")
            print("[Q] Encerrar")
            print("-" * 45)

            acao = ler_acao_usuario()

            if acao == "1":
                inseriu = salvar_alias(
                    conn,
                    alias_normalizado,
                    fornecedor["codigo_fornecedor"],
                    "sugerido_fuzzy",
                )
                if inseriu:
                    salvos += 1
                    print("Alias salvo com sucesso.")
                else:
                    print("Alias ja existia. Nada foi alterado.")
                break

            if acao == "2":
                pulados += 1
                print("Alias pulado.")
                break

            if acao == "3":
                while True:
                    codigo_manual = input("Digite o codigo do fornecedor: ").strip()
                    fornecedor_manual = buscar_fornecedor_por_codigo(codigo_manual, conn=conn)
                    if not fornecedor_manual:
                        print("Codigo nao encontrado na tabela fornecedores. Tente novamente.")
                        continuar = input("Digitar outro codigo? [S/N]: ").strip().upper()
                        if continuar != "S":
                            pulados += 1
                            break
                        continue

                    inseriu = salvar_alias(
                        conn,
                        alias_normalizado,
                        fornecedor_manual["codigo_fornecedor"],
                        "manual",
                    )
                    if inseriu:
                        salvos += 1
                        print(
                            f'Alias salvo com codigo {fornecedor_manual["codigo_fornecedor"]} '
                            f'({fornecedor_manual["nome_oficial"]}).'
                        )
                    else:
                        print("Alias ja existia. Nada foi alterado.")
                    break
                break

            if acao == "Q":
                encerrar = True
                break

        if encerrar:
            break

    return analisados, salvos, pulados, sem_sugestao


def main():
    conn = get_connection()
    try:
        candidatos = coletar_candidatos(conn)
        if not candidatos:
            print("Nenhum candidato encontrado para sugestao de aliases.")
            print("Proximo passo: python app.py --so-auto")
            return

        print(f"Candidatos encontrados: {len(candidatos)}")
        print("Iniciando revisao interativa de aliases sugeridos...\n")

        analisados, salvos, pulados, sem_sugestao = processar_candidatos(conn, candidatos, threshold=70)

        print("\n" + "=" * 45)
        print(f"Total de candidatos analisados: {analisados}")
        print(f"Aliases confirmados e salvos:   {salvos}")
        print(f"Pulados:                        {pulados}")

        if sem_sugestao:
            print("\nSem sugestao automatica - requerem alias manual:")
            for alias in sem_sugestao:
                print(f"  - {alias}")

        print("\nProximo passo: python app.py --so-auto")
        print("=" * 45)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
