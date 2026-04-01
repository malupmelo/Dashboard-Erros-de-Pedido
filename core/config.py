# ─────────────────────────────────────────────
# config.py — Configurações centralizadas
# Para alterar qualquer configuração do projeto,
# edite apenas este arquivo.
# ─────────────────────────────────────────────

import os

# Raiz do projeto (um nível acima de core/)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Banco de dados
DB_PATH = os.path.join(BASE_DIR, "erros_pedido.db")

# Pasta de dados
PASTA_DATA = os.path.join(BASE_DIR, "data")

# Planilha oficial utilizada pelo sistema
ARQUIVO_FLUXO_EMAILS = os.path.join(PASTA_DATA, "Fluxo_Emails.xlsx.xlsx")

# Sincronização automática das planilhas
# Intervalo em segundos para checar mudanças na pasta data/
AUTO_REIMPORT_INTERVALO_SEGUNDOS = 60
# Se True, só reimporta quando detectar alteração em arquivo .xlsx
AUTO_REIMPORT_SOMENTE_SE_ALTERAR = True

# Limite de linhas para leitura do Excel (evita planilhas com 1.048.576 linhas formatadas)
LEITURA_EXCEL_NROWS_MAX = 20000

# Se True, copia automaticamente para data/ o arquivo homônimo mais novo encontrado no OneDrive
SINCRONIZAR_HOMONIMOS_MAIS_NOVOS = False

# Servidor
HOST = "0.0.0.0"
PORT = 5000
DEBUG = False

# Colunas obrigatórias da planilha Excel
COLUNAS_OBRIGATORIAS = {"NF", "FORNECEDOR", "PEDIDO", "ERRO", "DATA", "COMPRADOR", "ASSUNTO", "REMETENTE"}

# ─────────────────────────────────────────────
# CATEGORIAS DE ERRO
# ─────────────────────────────────────────────
# Um erro pode pertencer a MÚLTIPLAS categorias.
# O sistema verifica todas as palavras-chave e
# contabiliza em cada categoria que se aplicar.
#
# Para adicionar nova categoria:
#   ("Nome da Categoria", ["palavra1", "palavra2"]),
# ─────────────────────────────────────────────
CATEGORIAS = [
    ("IVA",                         ["iva"]),
    ("Confirmação de Recebimento",  ["recebimento", "entrada", "desmarcar entrada"]),
    ("Fatura Final",                ["fatura final", "fechada", "item final"]),
    ("Preço",                       ["valor unitário", "valor unitario", "ajuste de valor", "ajuste valor", "faturado", "valor", "pc", "maior", "menor", "unitário", "unitario", "kg"]),
    ("Erro de CNPJ",                ["cnpj"]),
    ("NCM",                         ["ncm"]),
    ("RevFatEM",                    ["revfatem"]),
    ("Incoterms",                   ["incoterms"]),
    ("Alíquota de ICMS",            ["icms", "alíquota", "aliquota", "gnre", "pagamento st", "guia e pagamento st", "guia gnre"]),
    ("Código/Serviço",              ["código", "code", "serviço", "servico", "alterar todos itens", "modificar linha", "origem do material", "para yd", "para yg", "para cj", "para ye", "para c0"]),
    ("Aprovação",                   ["aprovação", "aprovaçao", "aprovado"]),
    ("Desconto",                    ["desconto"]),
    ("Parceiro",                    ["parceiro", "prestador", "matriz", "distribuição", "distribuicao"]),
    ("Suplementação",               ["frete", "suplementar", "fr03", "suplementação"]),
]

CATEGORIA_PADRAO = "Outros"

# ─────────────────────────────────────────────
# CORES DAS CATEGORIAS NO DASHBOARD
# Para mudar uma cor, edite o valor hex aqui.
# ─────────────────────────────────────────────
CORES_CATEGORIAS = {
    "IVA":                        "#0f3460",
    "Confirmação de Recebimento": "#2a9d8f",
    "Fatura Final":               "#457b9d",
    "Preço":                      "#f4a261",
    "Erro de CNPJ":               "#e63946",
    "NCM":                        "#e9c46a",
    "RevFatEM":                   "#264653",
    "Incoterms":                  "#6d6875",
    "Alíquota de ICMS":           "#e76f51",
    "Código/Serviço":             "#3a86ff",
    "Aprovação":                  "#8338ec",
    "Desconto":                   "#a8dadc",
    "Parceiro":                   "#7e22ce",
    "Suplementação":              "#16a34a",
    "Outros":                     "#aaaaaa",
}
