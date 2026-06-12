import sqlite3
import bcrypt

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

usuario = "admin"
senha = "123"
tipo = "master"

senha_hash = bcrypt.hashpw(
    senha.encode(),
    bcrypt.gensalt()
).decode()

cursor.execute("""
INSERT OR REPLACE INTO usuarios
(usuario, senha, tipo)
VALUES (?, ?, ?)
""", (
    usuario,
    senha_hash,
    tipo
))

conn.commit()
conn.close()

print("✔ Usuário criado")