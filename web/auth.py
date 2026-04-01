from flask import redirect, render_template_string, request, session, url_for

USUARIOS = {
    "eduardo.ribeiro": "erros2026",
    "carlos.everaldo": "erros2026",
    "jose.porto": "erros2026",
    "analista.gcb": "erros123"
}

HTML_LOGIN = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Login — Dashboard de Erros</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/dashboard.css') }}">
  <style>
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #f0f2f5;
      font-family: 'Segoe UI', Arial, sans-serif;
      padding: 16px;
    }
    .login-wrap {
      width: 100%;
      max-width: 420px;
    }
    .login-card {
      border-left: 4px solid #0f3460;
    }
    .login-title {
      font-size: 1.15rem;
      font-weight: 700;
      color: #1a1a2e;
      margin-bottom: 6px;
    }
    .login-subtitle {
      font-size: 0.78rem;
      color: #6b7280;
      margin-bottom: 18px;
    }
    .login-field {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 12px;
    }
    .login-field label {
      font-size: 0.72rem;
      font-weight: 700;
      color: #6b7280;
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }
    .login-field input {
      height: 38px;
      border: 1px solid #e5e7eb;
      border-radius: 7px;
      padding: 6px 10px;
      font-size: 0.84rem;
      color: #374151;
      outline: none;
      background: #fff;
    }
    .login-field input:focus {
      border-color: #93a7c6;
      box-shadow: 0 0 0 2px rgba(147, 167, 198, 0.16);
    }
    .login-error {
      border: 1px solid #f2d7d9;
      background: #fffdfd;
      color: #a11a2b;
      border-radius: 8px;
      padding: 10px;
      font-size: 0.8rem;
      margin-bottom: 12px;
    }
    .login-actions {
      display: flex;
      justify-content: flex-end;
    }
    .login-btn {
      min-width: 140px;
      height: 38px;
    }
  </style>
</head>
<body>
  <div class="container login-wrap">
    <div class="card login-card">
      <div class="login-title">Acesso ao Dashboard</div>
      <div class="login-subtitle">Entre com seu usuário e senha para continuar.</div>

      {% if erro %}
      <div class="login-error">{{ erro }}</div>
      {% endif %}

      <form method="post" action="{{ url_for('login') }}">
        <div class="login-field">
          <label for="usuario">Usuário</label>
          <input id="usuario" name="usuario" type="text" required autocomplete="username">
        </div>

        <div class="login-field">
          <label for="senha">Senha</label>
          <input id="senha" name="senha" type="password" required autocomplete="current-password">
        </div>

        <div class="login-actions">
          <button type="submit" class="btn login-btn">Entrar</button>
        </div>
      </form>
    </div>
  </div>
</body>
</html>
"""


def init_auth(app):
    @app.before_request
    def proteger_rotas():
        endpoint = request.endpoint or ""
        caminho = request.path or ""

        if endpoint in {"login", "logout", "static"} or caminho.startswith("/static/"):
            return None

        usuario_sessao = session.get("usuario")
        logado = bool(session.get("logado"))
        usuario_valido = bool(usuario_sessao) and usuario_sessao in USUARIOS

        if not logado or not usuario_valido:
            session.clear()
            return redirect(url_for("login"))

        return None

    @app.route("/login", methods=["GET", "POST"])
    def login():
      if request.method == "GET" and session.get("logado"):
        session.clear()

        if request.method == "POST":
            usuario = (request.form.get("usuario") or "").strip()
            senha = request.form.get("senha") or ""

            if USUARIOS.get(usuario) == senha:
                session["logado"] = True
                session["usuario"] = usuario
                return redirect(url_for("main.index"))

            return render_template_string(
                HTML_LOGIN,
                erro="Usuário ou senha inválidos.",
            )

        return render_template_string(HTML_LOGIN, erro=None)

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))
