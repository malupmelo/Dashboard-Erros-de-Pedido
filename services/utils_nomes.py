import re
import unicodedata
from collections import Counter, defaultdict


CONNECTORS = {"de", "da", "do", "dos", "das", "e"}
GENERIC_STOPWORDS = {
    "atenciosamente",
    "att",
    "atte",
    "best",
    "regards",
    "classificacao",
    "classificacao:",
    "uso",
    "interno",
    "suprimentos",
    "procurement",
    "compras",
    "materiais",
    "engenho",
    "varzea",
    "recife",
    "cep",
    "www",
    "http",
    "cid",
    "image",
    "contendo",
    "nome",
    "empresa",
    "descricao",
    "gerada",
    "automaticamente",
    "fone",
    "tel",
    "ramal",
    "whatsapp",
    "saludos",
    "cordialement",
    "ola",
    "oi",
    "boa",
    "dia",
    "tarde",
    "noite",
    "prezado",
    "prezados",
    "nao",
    "informado",
}


def remover_acentos(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    return "".join(ch for ch in texto if not unicodedata.combining(ch))


def limpar_comprador(texto_bruto: str) -> str:
    """Retorna nome limpo removendo email, assinaturas e ruido comum."""
    texto = (texto_bruto or "").strip()
    if not texto:
        return ""

    # Remove conteudo entre colchetes (ex.: [cid:image...]) e normaliza espacos
    texto = re.sub(r"\[.*?\]", " ", texto)
    texto = texto.replace("\r", "\n")

    # Se houver email, corta o texto a partir do inicio do email
    email_match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", texto)
    if email_match:
        texto = texto[: email_match.start()].strip()

    # Remove qualquer email residual
    texto = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", " ", texto)

    # Mantem apenas caracteres de texto e separadores simples
    texto = re.sub(r"[^A-Za-zÀ-ÖØ-öø-ÿ\s.'-]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip(" -:;,.|")

    # Remove tokens de login sem @ (ex.: camila.lima, junior_rodrigues)
    tokens = texto.split()
    tokens_filtrados = []
    login_like = re.compile(r"^[A-Za-z]{2,}(?:[._-][A-Za-z]{2,})+$")
    for tk in tokens:
        if login_like.match(tk):
            continue
        tokens_filtrados.append(tk)
    tokens = tokens_filtrados

    # Remove duplicacao de sufixo (ex.: "Camila Fonseca de Lima Camila")
    if not tokens:
        return ""

    if len(tokens) >= 4:
        metade = len(tokens) // 2
        if tokens[:metade] == tokens[metade : metade * 2]:
            tokens = tokens[:metade]

    return " ".join(tokens).strip()


def normalizar_nome_comprador(nome_limpo: str) -> str:
    """Normaliza para comparacao: lowercase, sem acento, sem pontuacao e sem conectores."""
    s = (nome_limpo or "").strip().lower()
    if not s:
        return ""

    s = remover_acentos(s)
    s = s.replace(".", " ")
    s = re.sub(r"[^a-z\s]", " ", s)
    tokens = [t for t in s.split() if t and t not in CONNECTORS]
    return " ".join(tokens)


def _tokens(normalizado: str) -> list[str]:
    return [t for t in (normalizado or "").split() if t]


def _token_match(a: str, b: str) -> bool:
    if a == b:
        return True
    if len(a) == 1 and b.startswith(a):
        return True
    if len(b) == 1 and a.startswith(b):
        return True
    return False


def comparar_compradores(nome1: str, nome2: str) -> float:
    """
    Compara dois nomes normalizados e retorna score [0,1].
    Peso maior para primeiro nome e ultimo sobrenome.
    """
    n1 = normalizar_nome_comprador(limpar_comprador(nome1))
    n2 = normalizar_nome_comprador(limpar_comprador(nome2))
    t1 = _tokens(n1)
    t2 = _tokens(n2)
    if not t1 or not t2:
        return 0.0

    score = 0.0

    # Primeiro nome obrigatorio para score alto
    if _token_match(t1[0], t2[0]):
        score += 0.45
    else:
        return 0.0

    # Sobrenome final com peso alto
    if len(t1) >= 2 and len(t2) >= 2 and _token_match(t1[-1], t2[-1]):
        score += 0.25

    # Interseccao geral de tokens (exceto primeiro)
    extras1 = t1[1:]
    extras2 = t2[1:]
    if extras1 and extras2:
        inter = 0
        for a in extras1:
            if any(_token_match(a, b) for b in extras2):
                inter += 1
        base = max(len(extras1), len(extras2))
        if base > 0:
            score += 0.25 * (inter / base)

    # Bonus pequeno para iniciais que batem
    if len(t1) >= 2 and len(t2) >= 2:
        if (len(t1[1]) == 1 and t2[1].startswith(t1[1])) or (len(t2[1]) == 1 and t1[1].startswith(t2[1])):
            score += 0.05

    return max(0.0, min(1.0, score))


def mesma_pessoa(nome1: str, nome2: str) -> bool:
    """Regra conservadora para agrupamento de compradores."""
    n1 = normalizar_nome_comprador(limpar_comprador(nome1))
    n2 = normalizar_nome_comprador(limpar_comprador(nome2))
    t1 = _tokens(n1)
    t2 = _tokens(n2)
    if not t1 or not t2:
        return False

    if not _token_match(t1[0], t2[0]):
        return False

    # Exemplo desejado: Daniela == Daniela N / Emerson == Emerson N.
    if len(t1) == 1 and len(t2) == 2 and len(t2[1]) == 1:
        return True
    if len(t2) == 1 and len(t1) == 2 and len(t1[1]) == 1:
        return True

    # Nome unico vs nome completo do mesmo primeiro nome (ex.: Camila)
    if len(t1) == 1 and len(t2) >= 2:
        return True
    if len(t2) == 1 and len(t1) >= 2:
        return True

    # Nao juntar iniciais conflitantes (Gabriel J. != Gabriel T.)
    if len(t1) >= 2 and len(t2) >= 2:
        if len(t1[1]) == 1 and len(t2[1]) == 1 and t1[1] != t2[1]:
            return False

    # Nao juntar nomes com meio claramente conflitante (Ana Maria != Ana Gabriela)
    if len(t1) >= 3 and len(t2) >= 3:
        meio1 = t1[1]
        meio2 = t2[1]
        if meio1 != meio2 and len(meio1) > 1 and len(meio2) > 1:
            return False

    # Nao juntar se sobrenomes finais diferentes e ambos completos
    if len(t1) >= 3 and len(t2) >= 3 and t1[-1] != t2[-1]:
        return False

    return comparar_compradores(nome1, nome2) >= 0.6


def _display_nome(nome_limpo: str) -> str:
    return " ".join(parte.capitalize() for parte in (nome_limpo or "").split())


def _canonico_do_grupo(membros: list[str], freq: Counter) -> str:
    """Escolhe nome canonico priorizando tokens completos, depois frequencia."""
    todos_tokens = []
    primeiros = []
    for nome in membros:
        norm = normalizar_nome_comprador(limpar_comprador(nome))
        toks = _tokens(norm)
        if toks:
            primeiros.append(toks[0])
        todos_tokens.extend(toks)

    if primeiros and all(p == "jose" for p in primeiros) and any(t in {"junior", "jr", "miguel"} for t in todos_tokens):
        return "Jose Junior"

    def rank(nome: str):
        limpo = limpar_comprador(nome)
        norm = normalizar_nome_comprador(limpo)
        toks = _tokens(norm)
        completos = sum(1 for t in toks if len(t) > 1)
        iniciais = sum(1 for t in toks if len(t) == 1)
        excesso = max(0, completos - 4)
        return (completos - excesso, -iniciais, freq[nome], len(limpo))

    escolhido = sorted(membros, key=rank, reverse=True)[0]
    return _display_nome(limpar_comprador(escolhido)) or "Nao Informado"


def agrupar_compradores(lista_nomes_brutos: list[str]) -> dict[str, str]:
    """Retorna mapa nome_bruto -> comprador_canonico com agrupamento conservador."""
    nomes = [n for n in (lista_nomes_brutos or []) if (n or "").strip()]
    if not nomes:
        return {}

    freq = Counter(nomes)
    unicos = sorted(freq.keys())

    parent = {n: n for n in unicos}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # So compara dentro do mesmo primeiro nome normalizado para reduzir falso positivo
    buckets = defaultdict(list)
    for n in unicos:
        norm = normalizar_nome_comprador(limpar_comprador(n))
        toks = _tokens(norm)
        if not toks:
            continue
        buckets[toks[0]].append(n)

    for grupo in buckets.values():
        # Evita agrupar apenas por primeiro nome quando ha multiplos sobrenomes distintos.
        segundos_tokens = set()
        for nome in grupo:
            toks = _tokens(normalizar_nome_comprador(limpar_comprador(nome)))
            if len(toks) >= 2:
                segundos_tokens.add(toks[1])

        for i in range(len(grupo)):
            for j in range(i + 1, len(grupo)):
                a, b = grupo[i], grupo[j]
                ta = _tokens(normalizar_nome_comprador(limpar_comprador(a)))
                tb = _tokens(normalizar_nome_comprador(limpar_comprador(b)))

                um_token_vs_completo = (
                    (len(ta) == 1 and len(tb) >= 2)
                    or (len(tb) == 1 and len(ta) >= 2)
                )
                if um_token_vs_completo and len(segundos_tokens) > 1:
                    continue

                if mesma_pessoa(a, b):
                    union(a, b)

    clusters = defaultdict(list)
    for n in unicos:
        clusters[find(n)].append(n)

    canonico = {}
    for membros in clusters.values():
        nome_canonico = _canonico_do_grupo(membros, freq)
        for n in membros:
            canonico[n] = nome_canonico

    return canonico


def preparar_campos_comprador(comprador_raw: str) -> dict[str, str]:
    """Gera campos intermediarios de comprador sem definir canonico final."""
    original = (comprador_raw or "").strip()
    limpo = limpar_comprador(original)
    normalizado = normalizar_nome_comprador(limpo)
    return {
        "comprador_original": original,
        "comprador_limpo": _display_nome(limpo) if limpo else "Nao Informado",
        "comprador_normalizado": normalizado,
    }
