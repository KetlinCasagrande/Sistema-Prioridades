import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("PRAGMA table_info(termos)")

for coluna in cursor.fetchall():
    print(coluna)

conn.close()