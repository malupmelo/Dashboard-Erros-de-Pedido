import sys
from pathlib import Path

# Adicionar o diretório raiz ao path para permitir imports
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

# Agora importar o script de importação
from scripts.importar_base_fornecedores import importar_base_fornecedores

if __name__ == "__main__":
    importar_base_fornecedores()
