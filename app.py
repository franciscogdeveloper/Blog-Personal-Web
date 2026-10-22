import os
from datetime import date
from pathlib import Path

from flask import Flask, abort, redirect, render_template, url_for

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


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        ARTICLES_DIR=os.environ.get("BLOG_ARTICLES_DIR", DEFAULT_ARTICLES_DIR),
    )
    # Los tests pasan aquí su propia configuración
    if config:
        app.config.update(config)

    store = ArticleStore(app.config["ARTICLES_DIR"])
    # Permite usar {{ fecha | long_date }} en las plantillas
    app.add_template_filter(long_date)

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

    return app
