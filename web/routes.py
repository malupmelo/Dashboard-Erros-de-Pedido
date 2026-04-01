# ─────────────────────────────────────────────
# routes.py — Rotas do servidor web
# Para adicionar novas páginas ou endpoints API,
# registre aqui.
# ─────────────────────────────────────────────

import json
from collections import Counter
from datetime import datetime
from io import BytesIO
from flask import Blueprint, render_template, jsonify, request, send_file
from core.database import buscar_registros, buscar_ultima_importacao, contar_registros
from services.analytics import enriquecer_registros, calcular_kpis, calcular_evolucao, calcular_alertas_criticos, parse_data_br
from core.config import CORES_CATEGORIAS, CATEGORIAS

bp = Blueprint("main", __name__)

@bp.after_request
# prevent browser caching of dashboard page
# synchronous function avoids async/extra requirements
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def _filtrar_registros(data_inicio: str, data_fim: str, fornecedor: str, categoria: str):
    """Aplica os mesmos filtros do endpoint de dashboard e retorna (todos, contexto, filtrados)."""
    registros = enriquecer_registros(buscar_registros())
    dt_inicio = parse_data_br(data_inicio)
    dt_fim = parse_data_br(data_fim)

    registros_contexto = []
    for r in registros:
        if fornecedor and r["fornecedor"] != fornecedor:
            continue
        if categoria and categoria not in r.get("categorias", []):
            continue
        registros_contexto.append(r)

    registros_filtrados = []
    for r in registros_contexto:
        dt_reg = parse_data_br(r["data"])
        if dt_inicio and dt_reg and dt_reg < dt_inicio:
            continue
        if dt_fim and dt_reg and dt_reg > dt_fim:
            continue
        registros_filtrados.append(r)

    return registros, registros_contexto, registros_filtrados


def _resumo_filtros(data_inicio: str, data_fim: str, fornecedor: str, categoria: str) -> str:
    partes = []
    if data_inicio:
        partes.append(f"De: {data_inicio}")
    if data_fim:
        partes.append(f"Até: {data_fim}")
    if fornecedor:
        partes.append(f"Fornecedor: {fornecedor}")
    if categoria:
        partes.append(f"Categoria: {categoria}")
    return " | ".join(partes) if partes else "Sem filtros aplicados"


def _gerar_pdf_relatorio(
    data_inicio: str,
    data_fim: str,
    fornecedor: str,
    categoria: str,
    registros_filtrados: list[dict],
    kpis: dict,
    categorias: list[tuple[str, int]],
    evolucao: list[tuple[str, int]],
    top_fornecedores: list[tuple[str, int]],
    top_compradores: list[tuple[str, int]],
    top_remetentes: list[tuple[str, int]],
) -> bytes:
    """Gera PDF em memória usando reportlab com dados filtrados do dashboard."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.graphics.shapes import Drawing, String
    from reportlab.graphics.charts.barcharts import VerticalBarChart
    from reportlab.graphics.charts.linecharts import HorizontalLineChart

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.2 * cm,
        rightMargin=1.2 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.2 * cm,
    )

    styles = getSampleStyleSheet()
    titulo = ParagraphStyle("titulo", parent=styles["Heading1"], fontSize=14, leading=18, spaceAfter=6)
    subtitulo = ParagraphStyle("subtitulo", parent=styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=12)
    secao = ParagraphStyle("secao", parent=styles["Heading2"], fontSize=11, spaceBefore=10, spaceAfter=6)
    normal = ParagraphStyle("normal", parent=styles["Normal"], fontSize=9, leading=11)

    story = []
    gerado_em = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    story.append(Paragraph("Relatório de Erros de Pedido (PDF)", titulo))
    story.append(Paragraph(f"Gerado em: {gerado_em}", subtitulo))
    story.append(Paragraph(f"Filtros: {_resumo_filtros(data_inicio, data_fim, fornecedor, categoria)}", normal))
    story.append(Spacer(1, 0.25 * cm))

    top1_comprador = top_compradores[0] if top_compradores else ("Nenhum", 0)
    top1_remetente = top_remetentes[0] if top_remetentes else ("Nenhum", 0)

    kpi_data = [
        ["KPIs Principais", "", "", ""],
        ["Total de Erros", str(kpis.get("total", 0)), "Total de Fornecedores", str(kpis.get("fornecedores", 0))],
        [
            "Categoria Mais Frequente",
            f"{kpis.get('categoria_mais_frequente', ('Nenhum', 0))[0]} ({kpis.get('categoria_mais_frequente', ('Nenhum', 0))[1]})",
            "Fornecedor com Mais Erros",
            f"{kpis.get('fornecedor_mais_erros', ('Nenhum', 0))[0]} ({kpis.get('fornecedor_mais_erros', ('Nenhum', 0))[1]})",
        ],
        ["Erros no Mês Atual", str(kpis.get("erros_mes_atual", 0)), "Total de Categorias", str(kpis.get("total_categorias", 0))],
        [
            "Top 1 Comprador",
            f"{top1_comprador[0]} ({top1_comprador[1]})",
            "Top 1 Remetente",
            f"{top1_remetente[0]} ({top1_remetente[1]})",
        ],
    ]
    t_kpi = Table(kpi_data, colWidths=[4.2 * cm, 5.0 * cm, 4.2 * cm, 5.0 * cm])
    t_kpi.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("SPAN", (0, 0), (-1, 0)),
        ("ALIGN", (0, 0), (-1, 0), "LEFT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(t_kpi)

    story.append(Paragraph("Visualizações", secao))
    draw = Drawing(500, 340)

    top_plot = top_fornecedores[:5]
    if top_plot:
        data_vals = [x[1] for x in top_plot]
        labels = [x[0][:16] for x in top_plot]
        bc = VerticalBarChart()
        bc.x = 20
        bc.y = 170
        bc.height = 120
        bc.width = 210
        bc.data = [data_vals]
        bc.categoryAxis.categoryNames = labels
        bc.valueAxis.valueMin = 0
        bc.bars[0].fillColor = colors.HexColor("#0f3460")
        bc.categoryAxis.labels.angle = 25
        bc.categoryAxis.labels.fontSize = 6
        bc.valueAxis.labels.fontSize = 7
        draw.add(String(20, 298, "Top Fornecedores", fontSize=8))
        draw.add(bc)

    cat_plot = categorias[:8]
    if cat_plot:
        data_vals = [x[1] for x in cat_plot]
        labels = [x[0][:14] for x in cat_plot]
        bc2 = VerticalBarChart()
        bc2.x = 265
        bc2.y = 170
        bc2.height = 120
        bc2.width = 210
        bc2.data = [data_vals]
        bc2.categoryAxis.categoryNames = labels
        bc2.valueAxis.valueMin = 0
        bc2.bars[0].fillColor = colors.HexColor("#16213e")
        bc2.categoryAxis.labels.angle = 25
        bc2.categoryAxis.labels.fontSize = 6
        bc2.valueAxis.labels.fontSize = 7
        draw.add(String(265, 298, "Categorias de Erro", fontSize=8))
        draw.add(bc2)

    evo_plot = evolucao[:12]
    if evo_plot:
        lc = HorizontalLineChart()
        lc.x = 20
        lc.y = 20
        lc.height = 120
        lc.width = 455
        lc.data = [[v for _, v in evo_plot]]
        lc.categoryAxis.categoryNames = [m[2:] if len(m) == 7 else m for m, _ in evo_plot]
        lc.valueAxis.valueMin = 0
        lc.lines[0].strokeColor = colors.HexColor("#1a1a2e")
        lc.lines[0].strokeWidth = 1.4
        lc.categoryAxis.labels.fontSize = 6
        lc.valueAxis.labels.fontSize = 7
        draw.add(String(20, 148, "Evolução Mensal de Erros", fontSize=8))
        draw.add(lc)

    story.append(draw)

    story.append(Paragraph("Análise por Categoria", secao))
    cat_data = [["Categoria", "Quantidade"]] + [[nome, str(qtd)] for nome, qtd in categorias]
    if len(cat_data) == 1:
        cat_data.append(["Sem dados", "0"])
    t_cat = Table(cat_data, colWidths=[13.5 * cm, 4.9 * cm])
    t_cat.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_cat)

    story.append(Paragraph("Top 5 Compradores com Mais Erros", secao))
    compradores_data = [["Comprador", "Quantidade"]] + [[nome, str(qtd)] for nome, qtd in top_compradores[:5]]
    if len(compradores_data) == 1:
        compradores_data.append(["Sem dados", "0"])
    t_compradores = Table(compradores_data, colWidths=[13.5 * cm, 4.9 * cm])
    t_compradores.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_compradores)

    story.append(Paragraph("Top 5 Remetentes com Mais Erros", secao))
    remetentes_data = [["Remetente", "Quantidade"]] + [[nome, str(qtd)] for nome, qtd in top_remetentes[:5]]
    if len(remetentes_data) == 1:
        remetentes_data.append(["Sem dados", "0"])
    t_remetentes = Table(remetentes_data, colWidths=[13.5 * cm, 4.9 * cm])
    t_remetentes.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story.append(t_remetentes)

    story.append(PageBreak())
    story.append(Paragraph("Tabela Detalhada de Erros (Filtrados)", secao))

    headers = ["Data", "NF", "Fornecedor", "Pedido", "Erro", "Comprador", "Categorias"]
    linhas = [headers]
    for r in registros_filtrados:
        cats = ", ".join(r.get("categorias", [])) or "Outros"
        linhas.append([
            (r.get("data") or "")[:10],
            str(r.get("nf") or "")[:16],
            str(r.get("fornecedor") or "")[:18],
            str(r.get("pedido") or "")[:12],
            str(r.get("erro") or "")[:42],
            str(r.get("comprador") or "")[:16],
            cats[:25],
        ])

    if len(linhas) == 1:
        linhas.append(["-", "-", "-", "-", "Sem registros para os filtros informados", "-", "-"])

    col_larguras = [1.8 * cm, 2.0 * cm, 3.1 * cm, 2.0 * cm, 6.1 * cm, 2.2 * cm, 2.0 * cm]
    tabela = Table(linhas, colWidths=col_larguras, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(tabela)

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


@bp.route("/")
def index():
    """Página principal do dashboard."""
    registros = enriquecer_registros(buscar_registros())
    kpis      = calcular_kpis(registros)
    alertas   = calcular_alertas_criticos(registros, registros)

    ultima    = buscar_ultima_importacao()
    ultima_importacao = (
        f"{ultima['importado_em']} ({ultima['registros']} registros)"
        if ultima else "Nenhuma importação"
    )

    from time import time
    html = render_template(
        "dashboard.html",
        records_json=json.dumps(registros, ensure_ascii=False),
        categorias_json=json.dumps([
            {"nome": nome, "chaves": chaves}
            for nome, chaves in CATEGORIAS
        ], ensure_ascii=False),
        kpis=kpis,
        alertas=alertas,
        ultima_importacao=ultima_importacao,
        total_banco=contar_registros(),
        data_min=registros[0]["data"]  if registros else "",
        data_max=registros[-1]["data"] if registros else "",
        fornecedores_lista=sorted(set(r["fornecedor"] for r in registros)),
        cores_json=json.dumps(CORES_CATEGORIAS, ensure_ascii=False),
        mes_atual_rotulo=datetime.now().strftime("%m/%Y"),
        now_timestamp=int(time())
    )
    return html


@bp.route("/api/dashboard-data", methods=["POST"])
def api_dashboard_data():
    """Endpoint único para todos os dados filtrados do dashboard."""
    data = request.get_json() or {}
    data_inicio = data.get("dataInicio", "").strip()
    data_fim = data.get("dataFim", "").strip()
    fornecedor = data.get("fornecedor", "").strip()
    categoria = data.get("categoria", "").strip()

    _, registros_contexto, registros_filtrados = _filtrar_registros(
        data_inicio,
        data_fim,
        fornecedor,
        categoria,
    )
    
    # Calcular todos os dados
    kpis = calcular_kpis(registros_filtrados)
    
    # Top fornecedores
    top_fornecedores = Counter(r["fornecedor"] for r in registros_filtrados).most_common(5)
    
    # Categorias
    cat_counter = Counter()
    for r in registros_filtrados:
        for cat in r.get("categorias", []):
            cat_counter[cat] += 1
    categorias = sorted(cat_counter.items(), key=lambda x: -x[1])
    
    # Evolução
    evolucao = calcular_evolucao(registros_filtrados)

    # Alertas críticos
    alertas = calcular_alertas_criticos(
        registros_filtrados,
        registros_contexto,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    
    # Top compradores
    top_compradores = Counter(r["comprador"] for r in registros_filtrados).most_common(5)
    top_remetentes = Counter(r.get("remetente_nome", "Não informado") for r in registros_filtrados).most_common(5)
    
    return jsonify({
        "kpis": kpis,
        "top_fornecedores": top_fornecedores,
        "categorias": categorias,
        "evolucao": evolucao,
        "top_compradores": top_compradores,
        "top_remetentes": top_remetentes,
        "alertas": alertas
    })


# ── API REST ──────────────────────────────────

@bp.route("/api/dados")
def api_dados():
    """Retorna todos os registros em JSON."""
    registros = enriquecer_registros(buscar_registros())
    return jsonify(registros)


@bp.route("/api/kpis")
def api_kpis():
    """Retorna os KPIs calculados em JSON."""
    registros = enriquecer_registros(buscar_registros())
    kpis = calcular_kpis(registros)
    return jsonify({
        k: v for k, v in kpis.items()
        if not isinstance(v, list)
    })


@bp.route("/exportar-pdf", methods=["GET"])
def exportar_pdf():
    """Exporta o relatório em PDF respeitando os filtros ativos."""
    data_inicio = (request.args.get("dataInicio") or "").strip()
    data_fim = (request.args.get("dataFim") or "").strip()
    fornecedor = (request.args.get("fornecedor") or "").strip()
    categoria = (request.args.get("categoria") or "").strip()

    _, registros_contexto, registros_filtrados = _filtrar_registros(
        data_inicio,
        data_fim,
        fornecedor,
        categoria,
    )

    kpis = calcular_kpis(registros_filtrados)
    top_fornecedores = Counter(r["fornecedor"] for r in registros_filtrados).most_common(5)
    top_compradores = Counter(r["comprador"] for r in registros_filtrados).most_common(5)
    top_remetentes = Counter(r.get("remetente_nome", "Não informado") for r in registros_filtrados).most_common(5)

    cat_counter = Counter()
    for r in registros_filtrados:
        for cat in r.get("categorias", []):
            cat_counter[cat] += 1
    categorias = sorted(cat_counter.items(), key=lambda x: -x[1])

    evolucao = calcular_evolucao(registros_filtrados)
    _ = calcular_alertas_criticos(
        registros_filtrados,
        registros_contexto,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )

    pdf_bytes = _gerar_pdf_relatorio(
        data_inicio=data_inicio,
        data_fim=data_fim,
        fornecedor=fornecedor,
        categoria=categoria,
        registros_filtrados=registros_filtrados,
        kpis=kpis,
        categorias=categorias,
        evolucao=evolucao,
        top_fornecedores=top_fornecedores,
        top_compradores=top_compradores,
        top_remetentes=top_remetentes,
    )

    nome_arquivo = f"relatorio_erros_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nome_arquivo,
    )
