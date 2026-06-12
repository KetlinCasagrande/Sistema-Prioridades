from flask import Blueprint, request, jsonify
from db import conectar
from auth import admin_required

api = Blueprint("api", __name__)
api_bp = Blueprint("api", __name__)
# ========================
# DELETE COMISSÃO
# ========================
@api.route("/comissao/delete/<int:id>", methods=["DELETE"])
@admin_required
def delete_comissao(id):
    conn = conectar()
    cur = conn.cursor()

    cur.execute("DELETE FROM comissoes WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


# ========================
# CREATE COMISSÃO
# ========================
@api.route("/comissao/create", methods=["POST"])
@admin_required
def create_comissao():
    data = request.json

    conn = conectar()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO comissoes (banco, produto, comissao, score, prazo)
        VALUES (?, ?, ?, ?, ?)
    """, (
        data["banco"],
        data["produto"],
        data["comissao"],
        data["score"],
        data["prazo"]
    ))

    conn.commit()
    conn.close()

    return jsonify({"ok": True})