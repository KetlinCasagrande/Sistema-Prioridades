import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(usuarios)")
colunas = [c[1] for c in cursor.fetchall()]

if "tema" not in colunas:
    cursor.execute("""
        ALTER TABLE usuarios
        ADD COLUMN tema TEXT DEFAULT 'rose'
    """)
    print("Coluna tema criada.")
else:
    print("Coluna tema já existe.")

conn.commit()
conn.close()