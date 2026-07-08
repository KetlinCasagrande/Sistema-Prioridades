import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

bancos = [
    ("PAN", "", "", "https://PANconsig.pansolucoes.com.br/WebAutorizador/", ""),
    ("PICPAY", "", "", "https://consignado.picpay.com/", ""),
    ("PARANA BANCO", "", "", "https://portalcentralcorrespondente.paranabanco.com.br/", ""),
    ("BRB FLEX", "", "", "https://flex.consig360.com.br/", ""),
    ("SOMA", "", "", "https://sistema.somabp2.com.br/login", ""),
    ("FACTA", "", "", "https://desenv.facta.com.br/sistemaNovo/login.php", ""),
    ("HAPPY", "", "", "https://sistema.somabp2.com.br/privado/aceite-margem/91ea6733-442c-4b33-b87a-98e5759e3d04", ""),
    ("ICRED", "", "", "https://corban.icred.digital/home", ""),
    ("EASYCRED", "", "", "https://sistemaeasy.easycredtech.com.br/session/login", ""),
    ("C6", "", "", "https://c6.c6consig.com.br/", ""),
    ("QUALIBANKING", "", "", "https://quali.joinbank.com.br/sign-in", ""),
    ("TOTALCASH", "", "", "https://totalcash.net.br/login", ""),
    ("BMG", "", "", "https://www.bmgconsig.com.br/", ""),
    ("NBC", "", "", "https://consig.nbcbank.com.br/", ""),
    ("DAYCOVAL", "", "", "https://portaldecredito.daycoval.com.br/login", ""),
    ("MERCANTIL", "", "", "https://meu.bancomercantil.com.br/login", ""),
    ("V8", "", "", "https://app.v8sistema.com/signin", ""),
    ("VCTEX", "", "", "https://www.appvctex.com.br/login", ""),
    ("PRESENCA", "", "", "https://portal.presencabank.com.br/sign-in", ""),
    ("HUB CREDITO", "", "", "https://fgts.hubcredito.com.br/login", ""),
    ("CREFAZ", "", "", "https://crefazon.com.br/login", "")
]

for banco in bancos:

    cursor.execute("""
        SELECT id
        FROM bancos
        WHERE nome = ?
    """, (banco[0],))

    existe = cursor.fetchone()

    if existe:

        cursor.execute("""
            UPDATE bancos
            SET
                login = ?,
                senha = ?,
                link = ?,
                observacao = ?
            WHERE nome = ?
        """, (
            banco[1],
            banco[2],
            banco[3],
            banco[4],
            banco[0]
        ))

    else:

        cursor.execute("""
            INSERT INTO bancos
            (nome, login, senha, link, observacao)
            VALUES (?, ?, ?, ?, ?)
        """, banco)

conn.commit()
conn.close()

print("✅ Bancos sincronizados com sucesso!")