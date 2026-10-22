import secrets
from functools import wraps

from flask import current_app, redirect, session, url_for
from werkzeug.security import check_password_hash


# Comprueba el usuario y la contraseña contra los de la configuración
def check_credentials(username, password):
    expected_user = current_app.config["ADMIN_USER"]
    password_hash = current_app.config["ADMIN_PASSWORD_HASH"]

    # Tarda lo mismo aunque los textos difieran al inicio, así no da pistas por el tiempo
    user_ok = secrets.compare_digest(username.encode(), expected_user.encode())
    password_ok = check_password_hash(password_hash, password)
    return user_ok and password_ok


# Decorador: si no hay sesión de administrador, redirige al login
def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper
