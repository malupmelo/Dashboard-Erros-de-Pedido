/* ─────────────────────────────────────────────
   dashboard.js — Lógica do Dashboard
   ───────────────────────────────────────────── */

// Dados injetados pelo Jinja2 (definidos no template)
// allData, catColors são variáveis globais vindas do HTML

let chartTopForn, chartCatBarras, chartEvolucao, chartTopCompradores, chartTopRemetentes;
const FILTRO_CODIGO_NAO_ENCONTRADO_PREFIXO = "CODIGO_NAO_ENCONTRADO::";

const CORES_QUALIDADE = {
  codigo_exato: "#166534",
  nome_encontrado: "#22c55e",
  alias_manual: "#2563eb",
  fuzzy: "#f59e0b",
  nao_encontrado: "#dc2626"
};

// ── Categorização (espelha config.py) ─────────────────
const CATEGORIAS = Array.isArray(categoriasConfig) ? categoriasConfig : [];

function normalizarTexto(texto) {
  return texto
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function categorizar(erro) {
  const e = normalizarTexto(erro);
  const cats = CATEGORIAS.filter(c => c.chaves.some(k => e.includes(k))).map(c => c.nome);
  return cats.length ? cats : ["Outros"];
}

function counter(arr, key) {
  const c = {};
  arr.forEach(r => { c[r[key]] = (c[r[key]] || 0) + 1; });
  return c;
}

function fornecedorCanonicoRegistro(registro) {
  return (registro.fornecedor_exibicao || registro.fornecedor_canonico || "").trim();
}

function codigoNaoEncontradoSelecionado(valorFiltro) {
  return (valorFiltro || "").startsWith(FILTRO_CODIGO_NAO_ENCONTRADO_PREFIXO);
}

function codigoDoFiltroNaoEncontrado(valorFiltro) {
  if (!codigoNaoEncontradoSelecionado(valorFiltro)) return "";
  return valorFiltro.substring(FILTRO_CODIGO_NAO_ENCONTRADO_PREFIXO.length).trim();
}

function registroCorrespondeFornecedorFiltro(registro, valorFiltro) {
  if (!valorFiltro) return true;

  const codigoFiltro = codigoDoFiltroNaoEncontrado(valorFiltro);
  if (codigoFiltro) {
    const codigoRegistro = String(registro.codigo_fornecedor || "").replace(/\s+/g, "").trim();
    const tipoMatch = String(registro.tipo_match_fornecedor || "").trim();
    return tipoMatch === "codigo_nao_encontrado" && codigoRegistro === codigoFiltro;
  }

  return fornecedorCanonicoRegistro(registro) === valorFiltro;
}

// ── Renderização principal ────────────────────────────
function render(data) {
  renderGraficos(data);
}

function atualizarAlertas(alertas) {
  const mapeamento = [
    ["pico_erros", "alertPicoValor", "alertPicoSub"],
    ["categoria_dominante", "alertCategoriaValor", "alertCategoriaSub"],
    ["fornecedor_fora_padrao", "alertFornecedorValor", "alertFornecedorSub"],
    ["remetente_alto_volume", "alertRemetenteValor", "alertRemetenteSub"],
  ];

  mapeamento.forEach(([chave, valorId, subId]) => {
    const alerta = alertas[chave];
    const valorEl = document.getElementById(valorId);
    const subEl = document.getElementById(subId);
    const cardEl = valorEl ? valorEl.closest(".alert-card") : null;

    if (!alerta || !valorEl || !subEl || !cardEl) return;

    valorEl.textContent = alerta.valor;
    subEl.textContent = alerta.subtexto;
    cardEl.classList.toggle("critical", Boolean(alerta.critico));
  });
}

function percentual(parte, total) {
  if (!total) return 0;
  return (parte / total) * 100;
}

function formatarPercentual(valor) {
  return `${Number(valor || 0).toFixed(1)}%`;
}

function atualizarPainelQualidade(payload) {
  const total = Number(payload?.total || 0);
  const porTipo = payload?.por_tipo || {};
  const fuzzyScores = payload?.fuzzy_scores || {};
  const naoEncontrados = Array.isArray(payload?.nao_encontrados) ? payload.nao_encontrados : [];

  const mapa = [
    { chave: "codigo_exato", rotulo: "Código exato", cor: CORES_QUALIDADE.codigo_exato },
    { chave: "nome_encontrado", rotulo: "Nome exato", cor: CORES_QUALIDADE.nome_encontrado },
    { chave: "alias_manual", rotulo: "Alias manual", cor: CORES_QUALIDADE.alias_manual },
    { chave: "fuzzy", rotulo: "Fuzzy", cor: CORES_QUALIDADE.fuzzy },
    { chave: "nao_encontrado", rotulo: "Não encontrado", cor: CORES_QUALIDADE.nao_encontrado }
  ];

  const percentualEl = document.getElementById("qualidadePercentual");
  if (percentualEl) {
    percentualEl.textContent = formatarPercentual(payload?.percentual_resolvido || 0);
  }

  const progressEl = document.getElementById("qualidadeProgress");
  if (progressEl) {
    const segmentos = {
      codigo_exato: progressEl.querySelector(".seg-codigo"),
      nome_encontrado: progressEl.querySelector(".seg-nome"),
      alias_manual: progressEl.querySelector(".seg-alias"),
      fuzzy: progressEl.querySelector(".seg-fuzzy"),
      nao_encontrado: progressEl.querySelector(".seg-nao")
    };

    mapa.forEach(({ chave }) => {
      const valor = Number(porTipo[chave] || 0);
      const width = total ? percentual(valor, total) : 0;
      if (segmentos[chave]) {
        segmentos[chave].style.width = `${width.toFixed(2)}%`;
        segmentos[chave].title = `${chave}: ${valor} (${formatarPercentual(width)})`;
      }
    });
  }

  const legendaEl = document.getElementById("qualidadeLegenda");
  if (legendaEl) {
    legendaEl.innerHTML = mapa.map(({ chave, rotulo, cor }) => {
      const valor = Number(porTipo[chave] || 0);
      const pct = total ? percentual(valor, total) : 0;
      return `
        <div class="qualidade-legenda-item">
          <span class="qualidade-dot" style="background:${cor}"></span>
          <span>${rotulo}: <strong>${valor}</strong> (${formatarPercentual(pct)})</span>
        </div>
      `;
    }).join("");
  }

  const fuzzyEl = document.getElementById("qualidadeFuzzyScores");
  if (fuzzyEl) {
    fuzzyEl.textContent =
      `Fuzzy scores: >=90 (${Number(fuzzyScores.acima_90 || 0)}), ` +
      `82-89 (${Number(fuzzyScores.entre_82_90 || 0)}), ` +
      `70-81 (${Number(fuzzyScores.entre_70_82 || 0)})`;
  }

  const listaEl = document.getElementById("listaNaoEncontradosTop10");
  if (listaEl) {
    const top10 = naoEncontrados.slice(0, 10);
    if (!top10.length) {
      listaEl.innerHTML = "<li>Sem registros não identificados.</li>";
    } else {
      listaEl.innerHTML = top10.map((item) => {
        const original = item.fornecedor_original || "(vazio)";
        const normalizado = item.fornecedor_normalizado || "(vazio)";
        const ocorrencias = Number(item.ocorrencias || 0);
        return `<li><strong>${ocorrencias}x</strong> ${original} <em>(${normalizado})</em></li>`;
      }).join("");
    }
  }
}

function configurarBotaoSugerirAliases() {
  const btn = document.getElementById("btnExecutarSugerirAliases");
  const comandoEl = document.getElementById("comandoSugerirAliases");
  if (!btn || !comandoEl) return;

  btn.addEventListener("click", async () => {
    comandoEl.hidden = false;
    const comando = comandoEl.textContent || "python scripts/sugerir_aliases.py";
    try {
      await navigator.clipboard.writeText(comando);
      btn.textContent = "Comando copiado";
      setTimeout(() => {
        btn.textContent = "Executar sugerir_aliases.py";
      }, 1500);
    } catch (_) {
      btn.textContent = "Comando exibido";
      setTimeout(() => {
        btn.textContent = "Executar sugerir_aliases.py";
      }, 1500);
    }
  });
}

async function carregarQualidadeFornecedores() {
  try {
    const response = await fetch("/api/qualidade-fornecedores");
    if (!response.ok) {
      throw new Error(`Falha ao carregar qualidade: ${response.status}`);
    }
    const payload = await response.json();
    atualizarPainelQualidade(payload);
  } catch (error) {
    console.error("Erro ao carregar painel de qualidade de fornecedores:", error);
  }
}

function renderGraficos(data, dashboardData) {
  const topForn = dashboardData
    ? dashboardData.top_fornecedores
    : (() => {
        const m = {};
        data.forEach(r => {
          const nome = fornecedorCanonicoRegistro(r);
          if (!nome) return;
          m[nome] = (m[nome] || 0) + 1;
        });
        return Object.entries(m).sort((a,b)=>b[1]-a[1]).slice(0,5);
      })();

  const catSorted = dashboardData
    ? dashboardData.categorias
    : (() => {
        const catCounter = {};
        data.forEach(r => {
          const cats = r.categorias || categorizar(r.erro);
          cats.forEach(cat => { catCounter[cat] = (catCounter[cat] || 0) + 1; });
        });
        return Object.entries(catCounter).sort((a,b) => b[1] - a[1]);
      })();

  // ── Top 5 Fornecedores (barras horizontais) ─────────
  if (chartTopForn) chartTopForn.destroy();
  chartTopForn = new Chart(document.getElementById("chartTopForn"), {
    type: "bar",
    data: {
      labels: topForn.map(x => x[0]),
      datasets: [{
        label: "Erros",
        data: topForn.map(x => x[1]),
        backgroundColor: "#0f3460",
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: "y",
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, ticks: { stepSize: 1 } },
        y: { ticks: { font: { size: 11 } } }
      }
    }
  });

  // ── Categorias (barras verticais) ───────────────────
  if (chartCatBarras) chartCatBarras.destroy();
  chartCatBarras = new Chart(document.getElementById("chartCatBarras"), {
    type: "bar",
    data: {
      labels: catSorted.map(x => x[0]),
      datasets: [{
        data: catSorted.map(x => x[1]),
        backgroundColor: catSorted.map(x => catColors[x[0]] || "#aaa"),
        borderRadius: 6
      }]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: { ticks: { font: { size: 10 } } }
      }
    }
  });

  // ── Evolução de Erros por Mês ───────────────────────
  const evolucaoData = dashboardData
    ? dashboardData.evolucao
    : (() => {
        const m = {};
        data.forEach(r => {
          const dt = parseData(r.data);
          if (!dt) return;
          const y = dt.getFullYear();
          const mm = String(dt.getMonth() + 1).padStart(2, "0");
          const key = `${y}-${mm}`;
          m[key] = (m[key] || 0) + 1;
        });
        return Object.keys(m).sort().map(k => [k, m[k]]);
      })();

  if (chartEvolucao) chartEvolucao.destroy();
  chartEvolucao = new Chart(document.getElementById("chartEvolucao"), {
    type: "line",
    data: {
      labels: evolucaoData.map(e => formatarMesAno(e[0] || e.mes)),
      datasets: [{
        label: "Erros",
        data: evolucaoData.map(e => e[1] || e.count),
        borderColor: "#0f3460",
        backgroundColor: "rgba(15, 52, 96, 0.1)",
        tension: 0.1
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
    }
  });

  // ── Top 5 Compradores ──────────────────────────────
  const topCompradores = dashboardData
    ? dashboardData.top_compradores
    : (() => {
        const m = {};
        data.forEach(r => {
          const nome = r.comprador_exibicao || r.comprador_canonico || r.comprador || "Nao Informado";
          m[nome] = (m[nome] || 0) + 1;
        });
        return Object.entries(m).sort((a,b) => b[1] - a[1]).slice(0,5);
      })();

  if (chartTopCompradores) chartTopCompradores.destroy();
  chartTopCompradores = new Chart(document.getElementById("chartTopCompradores"), {
    type: "bar",
    data: {
      labels: topCompradores.map(([c]) => c),
      datasets: [{
        label: "Erros",
        data: topCompradores.map(([,v]) => v),
        backgroundColor: ["#0f3460","#16213e","#1a1a2e","#533483","#e94560"]
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
    }
  });

  // ── Top 5 Remetentes ───────────────────────────────
  const topRemetentes = dashboardData
    ? dashboardData.top_remetentes
    : (() => {
        const m = {};
        data.forEach(r => {
          const nome = r.remetente_nome || "Não informado";
          m[nome] = (m[nome] || 0) + 1;
        });
        return Object.entries(m).sort((a,b) => b[1] - a[1]).slice(0,5);
      })();

  if (chartTopRemetentes) chartTopRemetentes.destroy();
  chartTopRemetentes = new Chart(document.getElementById("chartTopRemetentes"), {
    type: "bar",
    data: {
      labels: topRemetentes.map(([nome]) => nome),
      datasets: [{
        label: "Erros",
        data: topRemetentes.map(([,valor]) => valor),
        backgroundColor: ["#2a9d8f", "#0f3460", "#457b9d", "#6d6875", "#f4a261"],
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { beginAtZero: true, ticks: { stepSize: 1 } },
        y: { ticks: { font: { size: 11 } } }
      }
    }
  });
}

// ── Filtros ───────────────────────────────────────────
function parseData(str) {
  if (!str) return null;
  const [d, m, y] = str.split("/");
  if (!d || !m || !y) return null;

  const dia = Number(d);
  const mes = Number(m);
  const ano = Number(y);
  const anoMax = new Date().getFullYear() + 1;

  if (!Number.isInteger(dia) || !Number.isInteger(mes) || !Number.isInteger(ano)) return null;
  if (ano < 2020 || ano > anoMax || mes < 1 || mes > 12 || dia < 1 || dia > 31) return null;

  const dt = new Date(`${String(ano).padStart(4, "0")}-${String(mes).padStart(2, "0")}-${String(dia).padStart(2, "0")}`);
  return Number.isNaN(dt.getTime()) ? null : dt;
}

function formatarMesAno(valor) {
  if (!valor) return "";
  const m = String(valor).match(/^(\d{4})-(\d{2})$/);
  if (!m) return valor;
  return `${m[2]}/${m[1]}`;
}

function filtrar() {
  const dataInicio = document.getElementById("dataInicio").value.trim();
  const dataFim    = document.getElementById("dataFim").value.trim();
  const forn       = document.getElementById("filtroForn").value;
  const cat        = document.getElementById("filtroCategoria").value;

  const dtInicio = parseData(dataInicio);
  const dtFim    = parseData(dataFim);

  return allData.filter(r => {
    const dtRegistro = parseData(r.data);
    const cats = r.categorias || categorizar(r.erro);
    if (dtInicio && dtRegistro && dtRegistro < dtInicio) return false;
    if (dtFim    && dtRegistro && dtRegistro > dtFim)    return false;
    if (!registroCorrespondeFornecedorFiltro(r, forn)) return false;
    if (cat  && !cats.includes(cat)) return false;
    return true;
  });
}

function aplicarFiltros() {
  atualizarDashboard();
}

function exportarPDF() {
  const dataInicio = document.getElementById("dataInicio").value.trim();
  const dataFim = document.getElementById("dataFim").value.trim();
  const forn = document.getElementById("filtroForn").value;
  const cat = document.getElementById("filtroCategoria").value;

  if (dataInicio && !parseData(dataInicio)) {
    alert("Data inicial inválida. Use DD/MM/AAAA.");
    return;
  }
  if (dataFim && !parseData(dataFim)) {
    alert("Data final inválida. Use DD/MM/AAAA.");
    return;
  }

  const params = new URLSearchParams();
  if (dataInicio) params.append("dataInicio", dataInicio);
  if (dataFim) params.append("dataFim", dataFim);
  if (forn) params.append("fornecedor", forn);
  if (cat) params.append("categoria", cat);

  const query = params.toString();
  const url = query ? `/exportar-pdf?${query}` : "/exportar-pdf";
  window.location.href = url;
}

async function atualizarDashboard() {
  const dataInicio = document.getElementById("dataInicio").value.trim();
  const dataFim    = document.getElementById("dataFim").value.trim();
  const forn       = document.getElementById("filtroForn").value;
  const cat        = document.getElementById("filtroCategoria").value;

  try {
    const response = await fetch("/api/dashboard-data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        dataInicio,
        dataFim,
        fornecedor: forn,
        categoria: cat
      })
    });

    const dashboardData = await response.json();

    // Atualizar KPIs
    document.getElementById("kTotal").textContent     = dashboardData.kpis.total;
    document.getElementById("kErroFreq").textContent   = dashboardData.kpis.categoria_mais_frequente[1];
    document.getElementById("kErroFreqSub").textContent =
      dashboardData.kpis.categoria_mais_frequente[0].substring(0,25) +
      (dashboardData.kpis.categoria_mais_frequente[0].length > 25 ? "..." : "");
    document.getElementById("kFornMais").textContent    = dashboardData.kpis.fornecedor_mais_erros[1];
    document.getElementById("kFornMaisSub").textContent =
      dashboardData.kpis.fornecedor_mais_erros[0].substring(0,25) +
      (dashboardData.kpis.fornecedor_mais_erros[0].length > 25 ? "..." : "");
    document.getElementById("kMesAtual").textContent    = dashboardData.kpis.erros_mes_atual;
    atualizarAlertas(dashboardData.alertas);

    // Renderizar gráficos com dados filtrados
    renderGraficos(filtrar(), dashboardData);

  } catch (error) {
    console.error("Erro ao atualizar dashboard:", error);
  }
}

function limparFiltros() {
  ["dataInicio","dataFim","filtroForn","filtroCategoria"].forEach(id => {
    document.getElementById(id).value = "";
  });
  atualizarDashboard();
}

// ── Render inicial ────────────────────────────────────
render(allData);
configurarBotaoSugerirAliases();
carregarQualidadeFornecedores();
