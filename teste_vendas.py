import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("SELECT id, usuario FROM usuarios")
print(cursor.fetchall())

conn.close()