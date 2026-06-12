import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(comissoes)")

colunas = cursor.fetchall()

for c in colunas:
    print(c)

conn.close()