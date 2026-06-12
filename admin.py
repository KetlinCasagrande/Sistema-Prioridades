from flask import Blueprint, render_template, request, redirect, session
from functools import wraps
from db import conectar
import bcrypt

# =========================
# BLUEPRINT
# =========================
admin_bp = Blueprint("admin", __name__)

# =========================
# PROTEÇÃO
# =========================
def master_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        if "usuario" not in session:
            return redirect("/")

        tipo = session.get("tipo", "").strip().lower()

        return f(*args, **kwargs)

    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):

        if "usuario" not in session:
            return redirect("/")

        tipo = session.get("tipo", "").strip().lower()


        return f(*args, **kwargs)

    return wrapper


# =========================
# ADMIN DASHBOARD
# =========================
@admin_bp.route("/admin")
@admin_required
def painel():

    conn = conectar()
    cursor = conn.cursor()

    # usuários
    cursor.execute("""
        SELECT *
        FROM usuarios
        ORDER BY id DESC
    """)
    usuarios = cursor.fetchall()

    # avisos
    cursor.execute("""
        SELECT *
        FROM avisos
        ORDER BY id DESC
    """)
    avisos = cursor.fetchall()

    # comissões (MASTER vê tudo)
    tipo = session.get("tipo", "").strip().lower()

    if tipo == "master":

        cursor.execute("""
            SELECT *
            FROM comissoes
            ORDER BY score DESC
        """)
        comissoes = cursor.fetchall()

    else:
        comissoes = []

    conn.close()

    return render_template(
        "admin.html",
        usuarios=usuarios,
        avisos=avisos,
        comissoes=comissoes,
        tipo=tipo
    )


# =========================
# USUÁRIOS
# =========================
@admin_bp.route("/admin/usuario/criar", methods=["POST"])
@admin_required
def criar_usuario():

    usuario = request.form["usuario"]
    senha = request.form["senha"]
    tipo = request.form["tipo"].strip().lower()

    senha_hash = bcrypt.hashpw(
        senha.encode(),
        bcrypt.gensalt()
    ).decode()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuarios
        (usuario, senha, tipo)
        VALUES (?, ?, ?)
    """, (
        usuario,
        senha_hash,
        tipo
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


@admin_bp.route("/admin/usuario/deletar/<int:id>")
@master_required
def deletar_usuario(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM usuarios
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/admin")


# =========================
# COMISSÕES
# =========================
@admin_bp.route("/admin/comissao/criar", methods=["POST"])
@master_required
def criar_comissao():

    data = request.form

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO comissoes
        (
            banco,
            produto,
            tabela_nome,
            comissao,
            prazo,
            score,
            promotora,
            ativo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        data["banco"],
        data["produto"],
        data["tabela_nome"],
        data["comissao"],
        data["prazo"],
        data["score"],
        data.get("promotora")
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


@admin_bp.route("/admin/comissao/editar/<int:id>", methods=["POST"])
@master_required
def editar_comissao(id):

    comissao = request.form["comissao"]
    prazo = request.form["prazo"]
    score = request.form["score"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE comissoes
        SET
            comissao = ?,
            prazo = ?,
            score = ?
        WHERE id = ?
    """, (
        comissao,
        prazo,
        score,
        id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


@admin_bp.route("/admin/comissao/deletar/<int:id>")
@master_required
def deletar_comissao(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM comissoes
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/admin")


# =========================
# AVISOS
# =========================
@admin_bp.route("/admin/aviso/criar", methods=["POST"])
@admin_required
def criar_aviso():

    titulo = request.form["titulo"]
    mensagem = request.form["mensagem"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO avisos
        (titulo, mensagem)
        VALUES (?, ?)
    """, (
        titulo,
        mensagem
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


@admin_bp.route("/admin/aviso/deletar/<int:id>")
@admin_required
def deletar_aviso(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM avisos
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/admin")
