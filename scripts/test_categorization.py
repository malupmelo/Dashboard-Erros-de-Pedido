#!/usr/bin/env python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from flask import Flask
from web.routes import bp
from core.database import init_db, buscar_registros
from services.analytics import enriquecer_registros, calcular_kpis

# Setup Flask
app = Flask(__name__)
app.register_blueprint(bp)
init_db()

with app.test_client() as client:
    resp = client.get("/")
    print(f"[GET /] Status: {resp.status_code}")
    if resp.status_code != 200:
        print("ERRO! Conteúdo recebido:")
        print(resp.data[:2000].decode("utf-8", errors="replace"))
    else:
        # Check KPI in API
        resp2 = client.post("/api/dashboard-data",
                           json={},
                           content_type="application/json")
        import json
        data = json.loads(resp2.data)
        print(f"[POST /api/dashboard-data] Status: {resp2.status_code}")
        print(f"KPI keys: {sorted(data['kpis'].keys())}")
        cat, count = data["kpis"]["categoria_mais_frequente"]
        print(f"Categoria mais frequente: {cat} ({count})")

