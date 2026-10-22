import tempfile
import unittest

from articles import ArticleError, ArticleStore, validate


class TestValidate(unittest.TestCase):
    # Devuelve los campos sin espacios sobrantes
    def test_valid_fields(self):
        self.assertEqual(validate("  Hola ", "2024-08-07", " Texto "), ("Hola", "2024-08-07", "Texto"))

    # Rechaza título vacío, título muy largo, fecha inválida y contenido vacío
    def test_invalid_fields(self):
        cases = [
            ("", "2024-08-07", "Texto"),
            ("x" * 201, "2024-08-07", "Texto"),
            ("Hola", "2024-02-30", "Texto"),
            ("Hola", "ayer", "Texto"),
            ("Hola", "2024-08-07", "   "),
        ]
        for title, published, content in cases:
            with self.subTest(title=title[:10], published=published, content=content):
                with self.assertRaises(ArticleError):
                    validate(title, published, content)


class TestArticleStore(unittest.TestCase):
    # Cada test usa una carpeta temporal vacía
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = ArticleStore(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # Crea el artículo con id 1 y lo guarda en 1.json
    def test_create_and_get(self):
        article = self.store.create("Hola", "2024-08-07", "Texto")

        self.assertEqual(article["id"], 1)
        self.assertEqual(self.store.get(1), article)
        self.assertIsNone(self.store.get(99))

    # Lista del más reciente al más antiguo
    def test_list_all_sorted_by_date(self):
        self.store.create("Viejo", "2024-07-01", "x")
        self.store.create("Nuevo", "2024-08-07", "x")
        self.store.create("Medio", "2024-07-20", "x")

        titles = [article["title"] for article in self.store.list_all()]

        self.assertEqual(titles, ["Nuevo", "Medio", "Viejo"])

    # Edita los datos sin cambiar el id
    def test_update(self):
        self.store.create("Original", "2024-08-01", "Texto")
        self.store.update(1, "Editado", "2024-08-02", "Otro texto")

        self.assertEqual(self.store.get(1)["title"], "Editado")

    # Elimina el archivo del artículo
    def test_delete(self):
        self.store.create("A", "2024-08-01", "x")
        self.store.create("B", "2024-08-02", "x")
        self.store.delete(1)

        self.assertIsNone(self.store.get(1))
        self.assertEqual(len(self.store.list_all()), 1)

    # Editar o eliminar un id inexistente lanza ArticleError
    def test_missing_id(self):
        with self.assertRaises(ArticleError):
            self.store.update(99, "Hola", "2024-08-07", "Texto")
        with self.assertRaises(ArticleError):
            self.store.delete(99)

    # Un archivo dañado se informa como ArticleError
    def test_corrupted_file(self):
        (self.store.directory / "1.json").write_text("basura", encoding="utf-8")

        with self.assertRaises(ArticleError):
            self.store.get(1)
