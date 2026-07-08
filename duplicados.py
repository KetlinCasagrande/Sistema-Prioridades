import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

cursor.execute("""
DELETE FROM bancos
WHERE id NOT IN (
    SELECT MIN(id)
    FROM bancos
    GROUP BY nome
)
""")

conn.commit()

print("Duplicados removidos!")

conn.close()