import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(comissoes)")

for coluna in cursor.fetchall():
    print(coluna)

conn.close()