import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

try:

    cursor.execute("""
        ALTER TABLE comissoes
        ADD COLUMN status TEXT
    """)

    print("✔ Coluna status adicionada")

except Exception as e:
    print("⚠", e)

conn.commit()
conn.close()