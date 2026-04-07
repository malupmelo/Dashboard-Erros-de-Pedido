# ─────────────────────────────────────────────
# analytics.py — KPIs e cálculos do dashboard
# Para adicionar novos indicadores, edite aqui.
# ─────────────────────────────────────────────

from collections import Counter
from datetime import datetime, timedelta
import re
import unicodedata
from core.config import CATEGORIAS, CATEGORIA_PADRAO


def _normalizar_texto(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.lower())
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", texto).strip()


_CATEGORIAS_NORMALIZADAS = [
    (nome, [_normalizar_texto(chave) for chave in chaves])
    for nome, chaves in CATEGORIAS
]


def _categorias_especificas_ipi(erro_normalizado: str) -> list[str]:
    if "ipi" not in erro_normalizado:
        return []

    if (
        "diferente do pedido" in erro_normalizado
        or "diferente da nota" in erro_normalizado
        or "diferente do pc" in erro_normalizado
        or "diferente da pc" in erro_normalizado
        or "pedido/nota" in erro_normalizado
    ):
        return ["NCM"]

    if "por causa do ipi" in erro_normalizado and "alterar para" in erro_normalizado:
        return ["IVA"]

    return []


def categorizar(erro: str) -> list[str]:
    """
    Retorna TODAS as categorias que se aplicam ao erro.
    Um erro pode pertencer a múltiplas categorias.
    """
    e = _normalizar_texto(erro)
    cats = _categorias_especificas_ipi(e)
    if cats:
        return cats

    cats = []
    cats.extend(
        nome for nome, chaves in _CATEGORIAS_NORMALIZADAS
        if any(c in e for c in chaves) and nome not in cats
    )
    return cats if cats else [CATEGORIA_PADRAO]


def formatar_remetente(remetente: str) -> str:
    """Converte email ou texto bruto de remetente em nome amigável."""
    valor = (remetente or "").strip()
    if not valor:
        return "Não informado"

    email_match = re.search(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})", valor)
    if email_match:
        valor = email_match.group(1)

    valor = re.sub(r"[._\-+]+", " ", valor)
    valor = re.sub(r"\s+", " ", valor).strip(" <>\t\r\n")

    if not valor:
        return "Não informado"

    return " ".join(parte.capitalize() for parte in valor.split())


def parse_data_br(data_str: str):
    """Converte data DD/MM/YYYY em datetime; retorna None se inválida."""
    if not data_str:
        return None
    try:
        dt = datetime.strptime(data_str, "%d/%m/%Y")
        if dt.year < 2020 or dt.year > datetime.now().year + 1:
            return None
        return dt
    except ValueError:
        return None


def _resolver_aliases_remetentes(nomes: list[str]) -> dict[str, str]:
    """Une nomes curtos a um nome completo quando houver correspondência única."""
    nomes_unicos = sorted({nome for nome in nomes if nome and nome != "Não informado"})
    nomes_normalizados = {nome: _normalizar_texto(nome) for nome in nomes_unicos}
    aliases = {nome: nome for nome in nomes_unicos}

    for nome in nomes_unicos:
        partes = nome.split()
        if len(partes) != 1:
            continue

        primeiro_nome = nomes_normalizados[nome]
        candidatos = [
            candidato for candidato in nomes_unicos
            if len(candidato.split()) > 1
            and nomes_normalizados[candidato].split()[0] == primeiro_nome
        ]

        if len(candidatos) == 1:
            aliases[nome] = candidatos[0]

    return aliases


def fornecedor_canonico_valido(valor: str) -> bool:
    s = (valor or "").strip()
    if not s:
        return False

    s_lower = s.lower()
    if s.isdigit():
        return False
    if "@" in s or "\n" in s or "\r" in s:
        return False
    if "classificação: uso interno" in s_lower or "classificacao: uso interno" in s_lower:
        return False
    if "www." in s_lower or "cid:image" in s_lower:
        return False
    if s_upper := s.upper():
        if s_upper in {"FORNECEDOR NAO CADASTRADO", "NAO INFORMADO", "NÃO INFORMADO"}:
            return False

    return True


def fornecedor_canonico_registro(registro: dict) -> str:
    fornecedor_canonico = (registro.get("fornecedor_canonico") or "").strip()
    if fornecedor_canonico_valido(fornecedor_canonico):
        return fornecedor_canonico
    return ""


def enriquecer_registros(registros: list[dict]) -> list[dict]:
    """Adiciona lista de categorias a cada registro."""
    remetentes_formatados = []
    for r in registros:
        r["categorias"] = categorizar(r["erro"])
        r["remetente_nome"] = formatar_remetente(r.get("remetente", ""))
        r["fornecedor_exibicao"] = fornecedor_canonico_registro(r)
        comprador_canonico = (r.get("comprador_canonico") or "").strip()
        r["comprador_exibicao"] = comprador_canonico or r.get("comprador", "") or "Nao Informado"
        remetentes_formatados.append(r["remetente_nome"])

    aliases_remetentes = _resolver_aliases_remetentes(remetentes_formatados)
    for r in registros:
        r["remetente_nome"] = aliases_remetentes.get(r["remetente_nome"], r["remetente_nome"])

    return registros


def calcular_kpis(registros: list[dict]) -> dict:
    """
    Calcula todos os KPIs do dashboard.
    Para adicionar um novo KPI, inclua o cálculo aqui
    e referencie no templates/dashboard.html.
    """
    total = len(registros)
    if total == 0:
        return _kpis_vazios()

    # Contadores base
    fornecedores = Counter(
        r.get("fornecedor_exibicao") or fornecedor_canonico_registro(r)
        for r in registros
        if (r.get("fornecedor_exibicao") or fornecedor_canonico_registro(r))
    )
    remetentes = Counter(r.get("remetente_nome") or formatar_remetente(r.get("remetente", "")) for r in registros)

    # Categorias — um erro pode contar em múltiplas
    cat_counter = Counter()
    for r in registros:
        for cat in r.get("categorias", categorizar(r["erro"])):
            cat_counter[cat] += 1

    # Erros no mês atual
    mes_atual = datetime.now().strftime("%m/%Y")
    erros_mes_atual = sum(1 for r in registros if r["data"].endswith(mes_atual))

    # Categoria mais frequente (KPI melhorado - mostra categoria em vez de descrição de erro)
    categoria_mais_frequente = cat_counter.most_common(1)[0] if cat_counter else ("Nenhum", 0)

    # Fornecedor com mais erros
    fornecedor_mais_erros = fornecedores.most_common(1)[0] if fornecedores else ("Nenhum", 0)

    return {
        # ── KPIs principais ──────────────────────────
        "total":              total,
        "fornecedores":       len(fornecedores),
        "total_categorias":   len(cat_counter),

        # ── Novos KPIs solicitados ───────────────────
        "categoria_mais_frequente": categoria_mais_frequente,
        "fornecedor_mais_erros": fornecedor_mais_erros,
        "erros_mes_atual": erros_mes_atual,

        # ── Rankings ─────────────────────────────────
        "top_fornecedores":   fornecedores.most_common(5),
        "erros_por_fornecedor": sorted(fornecedores.items(), key=lambda x: -x[1]),

        # ── Distribuições ────────────────────────────
        "categorias":         sorted(cat_counter.items(), key=lambda x: -x[1]),

        # ── Novos ────────────────────────────────────
        "top_compradores":    Counter(r.get("comprador_exibicao", r.get("comprador", "Nao Informado")) for r in registros).most_common(5),
        "top_remetentes":    remetentes.most_common(5),
    }


def calcular_evolucao(registros: list[dict]) -> list[tuple[str, int]]:
    """
    Calcula a evolução de erros por mês/ano.
    Retorna lista ordenada de (mês-ano, contagem).
    """
    from collections import defaultdict

    evolucao = defaultdict(int)
    for r in registros:
        dt = parse_data_br(r.get("data", ""))
        if not dt:
            continue
        mes_ano = dt.strftime("%Y-%m")
        evolucao[mes_ano] += 1

    # Ordenar cronologicamente
    return sorted(evolucao.items())


def calcular_alertas_criticos(
    registros_filtrados: list[dict],
    registros_contexto: list[dict],
    data_inicio: str = "",
    data_fim: str = "",
    limite_fornecedor: int = 8,
) -> dict:
    """Calcula alertas críticos com base nos registros filtrados e no contexto comparável."""
    alertas = {
        "pico_erros": {
            "titulo": "🚨 Pico de erros",
            "valor": "Sem base comparativa",
            "subtexto": "Não há dados suficientes para comparação",
            "critico": False,
        },
        "categoria_dominante": {
            "titulo": "🚨 Categoria dominante",
            "valor": "Nenhuma",
            "subtexto": "Sem erros no período",
            "critico": False,
        },
        "fornecedor_fora_padrao": {
            "titulo": "🚨 Fornecedor fora do padrão",
            "valor": "Nenhum acima do limite",
            "subtexto": f"Limite crítico: mais de {limite_fornecedor} erros",
            "critico": False,
        },
        "remetente_alto_volume": {
            "titulo": "🚨 Analista / Remetente com alto volume",
            "valor": "Nenhum",
            "subtexto": "Sem ocorrências no período",
            "critico": False,
        },
    }

    total_filtrado = len(registros_filtrados)
    if total_filtrado == 0:
        return alertas

    datas_contexto = sorted(
        dt for dt in (parse_data_br(r.get("data", "")) for r in registros_contexto) if dt
    )
    datas_filtradas = sorted(
        dt for dt in (parse_data_br(r.get("data", "")) for r in registros_filtrados) if dt
    )

    dt_inicio_filtro = parse_data_br(data_inicio)
    dt_fim_filtro = parse_data_br(data_fim)

    if dt_inicio_filtro or dt_fim_filtro:
        periodo_inicio = dt_inicio_filtro or (datas_filtradas[0] if datas_filtradas else None)
        periodo_fim = dt_fim_filtro or (datas_filtradas[-1] if datas_filtradas else None)
        if periodo_inicio and periodo_fim and periodo_fim < periodo_inicio:
            periodo_inicio, periodo_fim = periodo_fim, periodo_inicio
        periodo_dias = ((periodo_fim - periodo_inicio).days + 1) if periodo_inicio and periodo_fim else 0
        periodo_anterior_fim = (periodo_inicio - timedelta(days=1)) if periodo_inicio else None
        periodo_anterior_inicio = (
            periodo_anterior_fim - timedelta(days=periodo_dias - 1)
            if periodo_anterior_fim and periodo_dias > 0 else None
        )
    else:
        periodo_fim = datas_contexto[-1] if datas_contexto else None
        periodo_inicio = periodo_fim.replace(day=1) if periodo_fim else None
        if periodo_inicio:
            periodo_anterior_fim = periodo_inicio - timedelta(days=1)
            periodo_anterior_inicio = periodo_anterior_fim.replace(day=1)
        else:
            periodo_anterior_inicio = None
            periodo_anterior_fim = None

    total_periodo_atual = total_filtrado
    total_anterior = 0
    if periodo_inicio and periodo_fim and not (dt_inicio_filtro or dt_fim_filtro):
        total_periodo_atual = sum(
            1
            for r in registros_contexto
            for dt in [parse_data_br(r.get("data", ""))]
            if dt and periodo_inicio <= dt <= periodo_fim
        )

    if periodo_anterior_inicio and periodo_anterior_fim:
        total_anterior = sum(
            1
            for r in registros_contexto
            for dt in [parse_data_br(r.get("data", ""))]
            if dt and periodo_anterior_inicio <= dt <= periodo_anterior_fim
        )

    if total_anterior > 0:
        variacao = ((total_periodo_atual - total_anterior) / total_anterior) * 100
        sinal = "+" if variacao >= 0 else ""
        alertas["pico_erros"] = {
            "titulo": "🚨 Pico de erros",
            "valor": f"{sinal}{variacao:.0f}% vs período anterior",
            "subtexto": f"{total_periodo_atual} no período atual vs {total_anterior} no anterior",
            "critico": variacao >= 20,
        }
    elif total_periodo_atual > 0:
        alertas["pico_erros"] = {
            "titulo": "🚨 Pico de erros",
            "valor": "Novo volume sem histórico",
            "subtexto": f"{total_periodo_atual} erros no período atual",
            "critico": total_periodo_atual >= 10,
        }

    cat_counter = Counter()
    for r in registros_filtrados:
        for cat in r.get("categorias", []):
            cat_counter[cat] += 1
    if cat_counter:
        categoria_nome, categoria_total = cat_counter.most_common(1)[0]
        percentual_categoria = (categoria_total / total_filtrado) * 100
        alertas["categoria_dominante"] = {
            "titulo": "🚨 Categoria dominante",
            "valor": f"{categoria_nome} = {percentual_categoria:.0f}% dos erros",
            "subtexto": f"{categoria_total} de {total_filtrado} ocorrências no período",
            "critico": percentual_categoria >= 40,
        }

    fornecedores = Counter(
        fornecedor_canonico_registro(r)
        for r in registros_filtrados
        if fornecedor_canonico_registro(r)
    )
    fornecedores_criticos = [(nome, total) for nome, total in fornecedores.most_common() if total > limite_fornecedor]
    if fornecedores_criticos:
        fornecedor_nome, fornecedor_total = fornecedores_criticos[0]
        alertas["fornecedor_fora_padrao"] = {
            "titulo": "🚨 Fornecedor fora do padrão",
            "valor": f"{fornecedor_nome} — {fornecedor_total} erros",
            "subtexto": f"Acima do limite crítico de {limite_fornecedor}",
            "critico": True,
        }

    remetentes = Counter(r.get("remetente_nome", "Não informado") for r in registros_filtrados)
    if remetentes:
        remetente_nome, remetente_total = remetentes.most_common(1)[0]
        alertas["remetente_alto_volume"] = {
            "titulo": "🚨 Analista / Remetente com alto volume",
            "valor": f"{remetente_nome} — {remetente_total} ocorrências",
            "subtexto": "Maior concentração de recebimento no período",
            "critico": remetente_total >= 10,
        }

    return alertas


def _kpis_vazios() -> dict:
    return {
        "total": 0, "fornecedores": 0, "total_categorias": 0,
        "categoria_mais_frequente": ("Nenhum", 0),
        "fornecedor_mais_erros": ("Nenhum", 0),
        "erros_mes_atual": 0,
        "top_fornecedores": [], "erros_por_fornecedor": [],
        "categorias": [],
        "top_compradores": [],
        "top_remetentes": [],
    }

