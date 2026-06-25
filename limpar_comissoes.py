import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("DELETE FROM comissoes")

conn.commit()
conn.close()

print("🧹 Todas as comissões removidas.")