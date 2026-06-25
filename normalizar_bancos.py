import sqlite3

DB = "banco.db"

MAPA_BANCOS = {
    "FACTA": "FACTA",
    "FACTA FINANCEIRA": "FACTA",
    "FACTA FINANCEIRA S.A": "FACTA",
    "FACTA S.A": "FACTA",
    "BANCO FACTA": "FACTA",

    "BMG": "BMG",
    "BANCO BMG": "BMG",
    "BMG CARD": "BMG",

    "DAYCOVAL": "DAYCOVAL",
    "BANCO DAYCOVAL": "DAYCOVAL",

    "C6": "C6 BANK",
    "C6 BANK": "C6 BANK",

    "PAN": "PAN",
    "BANCO PAN": "PAN",

    "PICPAY": "PICPAY",
    "PICPAY BANK": "PICPAY",
    "BANCO PICPAY": "PICPAY",
    "PICPAY BANK S.A": "PICPAY",
}

def limpar_texto(texto):
    if not texto:
        return ""

    texto = str(texto).strip()
    texto = " ".join(texto.split())
    return texto.upper()

def normalizar_banco(nome):
    nome_limpo = limpar_texto(nome)
    return MAPA_BANCOS.get(nome_limpo, nome_limpo)

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("SELECT id, banco FROM comissoes")
registros = cursor.fetchall()

alterados = 0

for id_comissao, banco_atual in registros:
    banco_novo = normalizar_banco(banco_atual)

    if banco_novo != banco_atual:
        cursor.execute("""
            UPDATE comissoes
            SET banco = ?
            WHERE id = ?
        """, (banco_novo, id_comissao))

        alterados += 1

conn.commit()
conn.close()

print(f"✅ Bancos normalizados: {alterados}")