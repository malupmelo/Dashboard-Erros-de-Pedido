from flask import redirect, render_template, request, session, url_for

USUARIOS = {
    "eduardo.ribeiro": "erros2026",
    "carlos.everaldo": "erros2026",
    "jose.porto": "erros2026",
    "analista.gcb": "erros123"
}

def init_auth(app):
  @app.after_request
  def desabilitar_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

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

      return render_template("login.html", erro="Usuário ou senha inválidos.")

    return render_template("login.html", erro=None)

  @app.route("/logout")
  def logout():
    session.clear()
    return redirect(url_for("login"))

