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
from web.app_factory import create_app
from core.config import (
    HOST,
    PORT,
    DEBUG,
    AUTO_REIMPORT_INTERVALO_SEGUNDOS,
    AUTO_REIMPORT_SOMENTE_SE_ALTERAR,
)
from core.database import init_db
from services.importer import importar_excel, importar_pasta_data
from services.background_sync import reimportar_em_background

app = create_app()


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