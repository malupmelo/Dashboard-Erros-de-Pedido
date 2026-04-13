import glob
import os
import time

from core.config import (
    AUTO_REIMPORT_INTERVALO_SEGUNDOS,
    AUTO_REIMPORT_SOMENTE_SE_ALTERAR,
    PASTA_DATA,
)
from services.importer import importar_pasta_data


def _snapshot_planilhas() -> dict[str, tuple[float, int]]:
    """Gera um snapshot simples dos arquivos .xlsx para detectar alterações."""
    snapshot: dict[str, tuple[float, int]] = {}
    padrao = os.path.join(PASTA_DATA, "*.xlsx")
    for caminho in sorted(glob.glob(padrao)):
        try:
            stat = os.stat(caminho)
            snapshot[os.path.basename(caminho)] = (stat.st_mtime, stat.st_size)
        except OSError:
            continue
    return snapshot


def reimportar_em_background() -> None:
    """Sincroniza a pasta data/ em segundo plano."""
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
