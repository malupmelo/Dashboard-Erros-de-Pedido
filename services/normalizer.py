# ─────────────────────────────────────────────
# normalizer.py — Funções compartilhadas de normalização de texto
# Fonte única de verdade para normalização de nomes de fornecedor.
# Usado por services/importer.py e scripts/importar_base_fornecedores.py.
# ─────────────────────────────────────────────

import re
import unicodedata

_TERMOS_REMOVER = {"ltda", "sa", "me", "eireli", "epp"}


def normalizar_nome_fornecedor(nome: str) -> str:
    """
    Normaliza um nome de fornecedor para comparação e busca:
    - lowercase
    - remove acentos
    - remove pontuação (exceto espaços e dígitos)
    - remove sufixos societários (ltda, sa, me, eireli, epp)
    - colapsa espaços múltiplos
    """
    s = (nome or "").strip().lower()
    if not s:
        return ""

    sem_acentos = unicodedata.normalize("NFKD", s)
    sem_acentos = "".join(ch for ch in sem_acentos if not unicodedata.combining(ch))
    sem_pontuacao = re.sub(r"[^a-z0-9\s]", " ", sem_acentos)
    tokens = re.sub(r"\s+", " ", sem_pontuacao).strip().split()
    filtrados = [t for t in tokens if t and t not in _TERMOS_REMOVER]
    return " ".join(filtrados)
