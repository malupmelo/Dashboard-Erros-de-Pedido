# Dashboard — Erros de Pedido
## Guia de Uso

---

## ESTRUTURA DO PROJETO

  app.py              → ponto de entrada e CLI
  web/app_factory.py   → criação da aplicação Flask e registro de blueprints
  core/config.py       → todas as configurações (cores, categorias, porta...)
  core/database.py     → operações com o banco de dados SQLite
  services/importer.py → leitura e importação da planilha oficial Fluxo_Emails
  services/analytics.py → cálculo de KPIs e categorização de erros
  services/background_sync.py → sincronização automática da pasta data/
  web/routes.py        → rotas do servidor web e API
  web/auth.py          → autenticação e proteção das rotas
  templates/
    dashboard.html    → estrutura HTML do dashboard
    login.html        → tela de login
  static/
    css/
      dashboard.css   → estilos visuais do dashboard
    js/
      dashboard.js    → lógica JS (gráficos, filtros, chamadas à API)
  scripts/
    audit_import.py   → script de auditoria da importação de dados
  data/
    Fluxo_Emails.xlsx.xlsx  → planilha oficial utilizada no dashboard
  requirements.txt    → dependências Python
  erros_pedido.db     → banco de dados (criado automaticamente)

Os arquivos antigos na raiz do projeto continuam como compatibilidade legada para scripts que ainda usam imports como `import analytics` ou `import database`.

---

## COMO USAR

  # Importar planilha e subir o servidor
  py app.py --importar Relatorio_Erros_Pedido_Formatado.xlsx

  # Importar automaticamente a planilha oficial de data/ e subir o servidor
  py app.py --auto

  # Só subir o servidor (sem importar)
  py app.py

  # Só importar (sem subir servidor)
  py app.py --so-importar Relatorio_Erros_Pedido_Formatado.xlsx

  # Só importar a planilha oficial de data/ (sem subir servidor)
  py app.py --so-auto

Acesse no navegador: http://localhost:5000
Para atualizar o dashboard: importe novamente e dê F5 no navegador

---

## COMO ADICIONAR UMA NOVA CATEGORIA DE ERRO

Edite o arquivo config.py e adicione uma linha em CATEGORIAS:

  CATEGORIAS = [
      ("IVA",             ["iva"]),
      ("Minha Categoria", ["palavra1", "palavra2"]),  ← adicione aqui
      ...
  ]

E adicione a cor em CORES_CATEGORIAS:

  CORES_CATEGORIAS = {
      "Minha Categoria": "#ff0000",  ← adicione aqui
      ...
  }

---

## COMO ADICIONAR UM NOVO KPI

Edite o arquivo analytics.py na função calcular_kpis():
  - Faça o cálculo
  - Adicione ao dicionário de retorno

Depois referencie no arquivo templates/dashboard.html.

---

## API REST

  GET  /api/dados          → todos os registros em JSON
  GET  /api/kpis           → KPIs calculados em JSON
  POST /api/dashboard-data → dados filtrados do dashboard (usado pelo JS)

---

## DEPENDÊNCIAS

  py -m pip install flask pandas openpyxl
