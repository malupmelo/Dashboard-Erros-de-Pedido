# ─────────────────────────────────────────────
# app.py — Ponto de entrada da aplicação
# ─────────────────────────────────────────────
#
# Uso:
#   py app.py                                        → sobe o servidor
#   py app.py --importar planilha.xlsx               → importa uma planilha e sobe
#   py app.py --importar p1.xlsx p2.xlsx             → importa várias e sobe
#   py app.py --auto                                 → importa pasta data/ e sobe
#   py app.py --so-importar planilha.xlsx            → só importa um arquivo
#   py app.py --so-auto                              → só importa pasta data/

import argparse
import threading
import time
import glob
import os
from flask import Flask
from config import (
    HOST,
    PORT,
    DEBUG,
    PASTA_DATA,
    AUTO_REIMPORT_INTERVALO_SEGUNDOS,
    AUTO_REIMPORT_SOMENTE_SE_ALTERAR,
)
from database import init_db
from importer import importar_excel, importar_pasta_data
from routes import bp

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.register_blueprint(bp)


def _snapshot_planilhas() -> dict[str, tuple[float, int]]:
    """Gera um snapshot simples dos arquivos .xlsx para detectar alterações."""
    snapshot = {}
    padrao = os.path.join(PASTA_DATA, "*.xlsx")
    for caminho in sorted(glob.glob(padrao)):
        try:
            stat = os.stat(caminho)
            snapshot[os.path.basename(caminho)] = (stat.st_mtime, stat.st_size)
        except OSError:
            continue
    return snapshot


def reimportar_em_background():
    """Sincroniza a pasta data/ em segundo plano.

    Se configurado, só reimporta quando detectar mudança em algum .xlsx.
    """
    ultimo_snapshot = None
    while True:
        try:
            snapshot_atual = _snapshot_planilhas()

            if AUTO_REIMPORT_SOMENTE_SE_ALTERAR and ultimo_snapshot == snapshot_atual:
                time.sleep(AUTO_REIMPORT_INTERVALO_SEGUNDOS)
                continue

            print("\n[REIMPORT] Sincronizando planilhas automaticamente...")
            importar_pasta_data()
            ultimo_snapshot = snapshot_atual
            print("[OK] Sincronizacao automatica concluida!")
        except Exception as e:
            print(f"[AVISO] Erro na sincronizacao automatica: {e}")

        time.sleep(AUTO_REIMPORT_INTERVALO_SEGUNDOS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dashboard de Erros de Pedido")
    parser.add_argument("--importar",    metavar="ARQUIVO", nargs="+", help="Importar uma ou mais planilhas específicas e iniciar servidor")
    parser.add_argument("--auto",        action="store_true", help="Importar automaticamente da pasta 'data/' e iniciar servidor")
    parser.add_argument("--so-importar", metavar="ARQUIVO", nargs="+", help="Só importar arquivo(s) específico(s), sem subir servidor")
    parser.add_argument("--so-auto",     action="store_true", help="Só importar automaticamente de 'data/', sem subir servidor")
    args = parser.parse_args()

    init_db()

    if args.so_importar:
        for arquivo in args.so_importar:
            importar_excel(arquivo)
        print("[OK] Importacao concluida.")
    elif args.so_auto:
        importar_pasta_data()
        print("[OK] Importacao concluida.")
    else:
        if args.importar:
            for arquivo in args.importar:
                importar_excel(arquivo)
        elif args.auto:
            importar_pasta_data()

        # Inicia reimportação automática em segundo plano
        t = threading.Thread(target=reimportar_em_background, daemon=True)
        t.start()
        print(f"\n Dashboard disponível em: http://localhost:{PORT}")
        print(
            "[REIMPORT] Sincronizacao automatica ativa "
            f"(a cada {AUTO_REIMPORT_INTERVALO_SEGUNDOS}s, "
            f"somente-se-alterar={AUTO_REIMPORT_SOMENTE_SE_ALTERAR})\n"
        )
        app.run(debug=DEBUG, host=HOST, port=PORT)