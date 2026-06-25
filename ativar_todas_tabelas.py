import sqlite3

DB = "banco.db"

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("""
    UPDATE comissoes
    SET ativo = 1
""")

print(f"✅ {cursor.rowcount} tabelas ativadas.")

conn.commit()
conn.close()

print("🚀 Processo concluído!")