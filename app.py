import os
import secrets
from datetime import date
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session, url_for

import auth
from articles import ArticleStore

# Nombres de los meses para mostrar las fechas en español
MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# Carpeta de artículos por defecto, junto a este archivo
DEFAULT_ARTICLES_DIR = Path(__file__).parent / "articles"


# Convierte "2024-08-07" en "7 de agosto de 2024"
def long_date(iso_date):
    day = date.fromisoformat(iso_date)
    return f"{day.day} de {MONTHS[day.month - 1]} de {day.year}"


# Token CSRF de la sesión; se crea la primera vez que se pide
def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("BLOG_SECRET_KEY"),
        ADMIN_USER=os.environ.get("BLOG_ADMIN_USER"),
        ADMIN_PASSWORD_HASH=os.environ.get("BLOG_ADMIN_PASSWORD_HASH"),
        ARTICLES_DIR=os.environ.get("BLOG_ARTICLES_DIR", DEFAULT_ARTICLES_DIR),
        # La cookie de sesión no se envía en formularios que vienen de otras webs
        SESSION_COOKIE_SAMESITE="Lax",
    )

    # Los tests pasan aquí su propia configuración
    if config:
        app.config.update(config)

    # Sin estas variables no se puede iniciar sesión ni firmar la cookie
    missing = [name for name in ("SECRET_KEY", "ADMIN_USER", "ADMIN_PASSWORD_HASH") if not app.config[name]]
    if missing:
        raise RuntimeError(f"Faltan variables de entorno para: {', '.join(missing)}. Revisa el README.")

    store = ArticleStore(app.config["ARTICLES_DIR"])
    # Permite usar {{ fecha | long_date }} en las plantillas
    app.add_template_filter(long_date)
    # csrf_token() queda disponible en todas las plantillas
    app.jinja_env.globals["csrf_token"] = csrf_token

    # Todo POST debe traer el mismo token CSRF que guarda la sesión
    @app.before_request
    def check_csrf():
        if request.method == "POST":
            sent = request.form.get("csrf_token", "")
            expected = session.get("csrf_token", "")
            if not expected or not secrets.compare_digest(sent, expected):
                abort(400)

    @app.route("/")
    def index():
        return redirect(url_for("home"))

    @app.route("/home")
    def home():
        return render_template("home.html", articles=store.list_all())

    @app.route("/article/<int:article_id>")
    def article(article_id):
        found = store.get(article_id)
        if found is None:
            abort(404)
        return render_template("article.html", article=found)

    @app.errorhandler(404)
    def not_found(error):
        return render_template("404.html"), 404

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            if auth.check_credentials(username, password):
                # Sesión nueva al entrar: no se reutiliza nada de una sesión anterior
                session.clear()
                session["is_admin"] = True
                return redirect(url_for("admin"))
            return render_template("login.html", error="Usuario o contraseña incorrectos."), 401
        return render_template("login.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("home"))

    @app.route("/admin")
    @auth.login_required
    def admin():
        return render_template("admin.html", articles=store.list_all())

    return app
