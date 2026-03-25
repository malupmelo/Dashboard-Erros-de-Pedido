# ─────────────────────────────────────────────
# routes.py — Rotas do servidor web
# Para adicionar novas páginas ou endpoints API,
# registre aqui.
# ─────────────────────────────────────────────

import json
from datetime import datetime
from flask import Blueprint, render_template, jsonify
from database import buscar_registros, buscar_ultima_importacao, contar_registros
from analytics import enriquecer_registros, calcular_kpis, calcular_evolucao, calcular_alertas_criticos, parse_data_br
from config import CORES_CATEGORIAS, CATEGORIAS

bp = Blueprint("main", __name__)

@bp.after_request
# prevent browser caching of dashboard page
# synchronous function avoids async/extra requirements
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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
    from flask import request
    import json
    from datetime import datetime
    from collections import Counter
    
    data = request.get_json()
    data_inicio = data.get("dataInicio", "").strip()
    data_fim = data.get("dataFim", "").strip()
    fornecedor = data.get("fornecedor", "").strip()
    categoria = data.get("categoria", "").strip()
    
    # Buscar e filtrar registros
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
        if dt_inicio and dt_reg and dt_reg < dt_inicio: continue
        if dt_fim and dt_reg and dt_reg > dt_fim: continue
        registros_filtrados.append(r)
    
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
