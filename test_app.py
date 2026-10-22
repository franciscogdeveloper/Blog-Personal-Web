import re
import tempfile
import unittest

from werkzeug.security import generate_password_hash

from app import create_app
from articles import ArticleStore

# Credenciales solo para los tests
TEST_USER = "admin"
TEST_PASSWORD = "clave-de-prueba"


class AppTestCase(unittest.TestCase):
    # Antes de cada test: app con credenciales de prueba y una carpeta de artículos vacía
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app({
            "TESTING": True,
            "SECRET_KEY": "clave-secreta-de-prueba",
            "ADMIN_USER": TEST_USER,
            "ADMIN_PASSWORD_HASH": generate_password_hash(TEST_PASSWORD),
            "ARTICLES_DIR": self.temp_dir.name,
        })
        self.client = self.app.test_client()
        self.store = ArticleStore(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    # Lee el token CSRF del formulario de una página
    def get_csrf_token(self, path):
        page = self.client.get(path).get_data(as_text=True)
        return re.search(r'name="csrf_token" value="([^"]+)"', page).group(1)

    # Inicia sesión como administrador
    def login(self, password=TEST_PASSWORD):
        token = self.get_csrf_token("/login")
        return self.client.post("/login", data={"username": TEST_USER, "password": password, "csrf_token": token})


class TestPublicPages(AppTestCase):
    # La raíz redirige a /home
    def test_root_redirects_to_home(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/home"))

    # La portada muestra los artículos, el más reciente primero, con la fecha en español
    def test_home_lists_articles(self):
        self.store.create("Primero", "2024-08-01", "Hola")
        self.store.create("Segundo", "2024-08-07", "Mundo")

        page = self.client.get("/home").get_data(as_text=True)

        self.assertLess(page.index("Segundo"), page.index("Primero"))
        self.assertIn("7 de agosto de 2024", page)

    # La página del artículo muestra su contenido; un id inexistente da 404
    def test_article_page(self):
        self.store.create("Primero", "2024-08-01", "Contenido del artículo")

        self.assertIn("Contenido del artículo", self.client.get("/article/1").get_data(as_text=True))
        self.assertEqual(self.client.get("/article/99").status_code, 404)

    # Lo que escribe el administrador se muestra como texto, no como HTML
    def test_title_is_escaped(self):
        self.store.create("<script>alert(1)</script>", "2024-08-01", "x")

        page = self.client.get("/home").get_data(as_text=True)

        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)


class TestAuthentication(AppTestCase):
    # Las páginas de administración redirigen al login sin sesión
    def test_admin_pages_require_login(self):
        for path in ["/admin", "/new", "/edit/1"]:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].endswith("/login"))

    # Una contraseña incorrecta responde 401 y no da acceso
    def test_wrong_password(self):
        response = self.login(password="incorrecta")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.client.get("/admin").status_code, 302)

    # Con las credenciales correctas se entra al panel, y al cerrar sesión se pierde el acceso
    def test_login_and_logout(self):
        self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 200)

        token = self.get_csrf_token("/admin")
        self.client.post("/logout", data={"csrf_token": token})

        self.assertEqual(self.client.get("/admin").status_code, 302)


class TestAdmin(AppTestCase):
    # Todos estos tests empiezan con la sesión de administrador iniciada
    def setUp(self):
        super().setUp()
        self.login()

    # Crea un artículo desde el formulario
    def test_create_article(self):
        token = self.get_csrf_token("/new")
        response = self.client.post("/new", data={
            "title": "Nuevo", "date": "2024-08-07", "content": "Texto", "csrf_token": token,
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.store.get(1)["title"], "Nuevo")

    # Un formulario inválido responde 400 y conserva lo escrito
    def test_create_invalid_article(self):
        token = self.get_csrf_token("/new")
        response = self.client.post("/new", data={
            "title": "Mi título", "date": "fecha-mala", "content": "Texto", "csrf_token": token,
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('value="Mi título"', response.get_data(as_text=True))
        self.assertEqual(self.store.list_all(), [])

    # Edita un artículo existente
    def test_edit_article(self):
        self.store.create("Original", "2024-08-01", "Texto")
        token = self.get_csrf_token("/edit/1")

        self.client.post("/edit/1", data={
            "title": "Editado", "date": "2024-08-02", "content": "Nuevo texto", "csrf_token": token,
        })

        self.assertEqual(self.store.get(1)["title"], "Editado")

    # Elimina un artículo
    def test_delete_article(self):
        self.store.create("Para borrar", "2024-08-01", "Texto")
        token = self.get_csrf_token("/admin")

        response = self.client.post("/delete/1", data={"csrf_token": token})

        self.assertEqual(response.status_code, 302)
        self.assertIsNone(self.store.get(1))

    # Un POST sin token CSRF se rechaza y no modifica nada
    def test_post_without_csrf_token_is_rejected(self):
        self.store.create("Protegido", "2024-08-01", "Texto")

        response = self.client.post("/delete/1")

        self.assertEqual(response.status_code, 400)
        self.assertIsNotNone(self.store.get(1))
