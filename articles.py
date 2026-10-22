import json
import os
from datetime import date
from pathlib import Path

# Largo máximo del título
MAX_TITLE_LENGTH = 200


# Error de validación o de lectura de un artículo
class ArticleError(Exception):
    pass


# Valida los campos del formulario y los devuelve sin espacios sobrantes
def validate(title, published, content):
    title = title.strip()
    published = published.strip()
    content = content.strip()

    if not title:
        raise ArticleError("El título no puede estar vacío.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ArticleError(f"El título no puede tener más de {MAX_TITLE_LENGTH} caracteres.")
    try:
        date.fromisoformat(published)
    except ValueError:
        raise ArticleError("La fecha de publicación no es válida.")
    if not content:
        raise ArticleError("El contenido no puede estar vacío.")

    return title, published, content


# Guarda cada artículo como un archivo JSON dentro de una carpeta
class ArticleStore:
    # Recibe la carpeta de los artículos y la crea si no existe
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    # Ruta del archivo de un artículo
    def _path(self, article_id):
        return self.directory / f"{article_id}.json"

    # Escribe el artículo en un archivo temporal y luego reemplaza el original
    def _save(self, article):
        path = self._path(article["id"])
        temp_file = path.with_suffix(".tmp")
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(article, file, indent=2, ensure_ascii=False)
        os.replace(temp_file, path)

    # Devuelve un artículo por id, o None si no existe
    def get(self, article_id):
        path = self._path(article_id)
        if not path.exists():
            return None
        try:
            with open(path, encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            raise ArticleError(f"El archivo {path.name} está dañado.")

    # Ids de todos los artículos guardados, según los nombres de archivo
    def _ids(self):
        return [int(path.stem) for path in self.directory.glob("*.json") if path.stem.isdigit()]

    # Todos los artículos, del más reciente al más antiguo
    def list_all(self):
        articles = [self.get(article_id) for article_id in self._ids()]
        return sorted(articles, key=lambda article: (article["date"], article["id"]), reverse=True)

    # Crea un artículo con el siguiente id disponible y lo devuelve
    def create(self, title, published, content):
        title, published, content = validate(title, published, content)
        article = {
            "id": max(self._ids(), default=0) + 1,
            "title": title,
            "date": published,
            "content": content,
        }
        self._save(article)
        return article

    # Reemplaza los datos de un artículo existente y lo devuelve
    def update(self, article_id, title, published, content):
        if self.get(article_id) is None:
            raise ArticleError(f"No existe un artículo con ID {article_id}.")
        title, published, content = validate(title, published, content)
        article = {"id": article_id, "title": title, "date": published, "content": content}
        self._save(article)
        return article

    # Elimina el archivo de un artículo
    def delete(self, article_id):
        path = self._path(article_id)
        if not path.exists():
            raise ArticleError(f"No existe un artículo con ID {article_id}.")
        path.unlink()
