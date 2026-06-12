import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("""
UPDATE bancos
SET login = ?, senha = ?
WHERE nome = ?
""", (
    "SEU_LOGIN_AQUI",
    "SUA_SENHA_AQUI",
    "PAN"
))

conn.commit()
conn.close()

print("✅ Banco atualizado!")