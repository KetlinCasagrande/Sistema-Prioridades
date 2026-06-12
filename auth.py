from flask import session, redirect
from functools import wraps

# =========================
# LOGIN REQUIRED
# =========================
def login_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if "usuario" not in session:
            return redirect("/")

        return f(*args, **kwargs)

    return wrapper


# =========================
# ADMIN REQUIRED
# =========================
def admin_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        return f(*args, **kwargs)

    return wrapper


# =========================
# MASTER REQUIRED
# =========================
def master_required(f):

    @wraps(f)
    def wrapper(*args, **kwargs):


        return f(*args, **kwargs)

    return wrapper