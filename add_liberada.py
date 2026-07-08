import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(comissoes)")
colunas = [coluna[1] for coluna in cursor.fetchall()]

if "liberada" not in colunas:
    cursor.execute("""
        ALTER TABLE comissoes
        ADD COLUMN liberada INTEGER DEFAULT 0
    """)
    print("Coluna liberada criada com sucesso.")
else:
    print("Coluna liberada já existe.")

conn.commit()
conn.close()
