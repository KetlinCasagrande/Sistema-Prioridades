import sqlite3
import os
from datetime import datetime


BANCO = "banco.db"
PASTA_BACKUP = "backups"


def fazer_backup(usuario="sistema"):

    # garante que a pasta exista
    os.makedirs(PASTA_BACKUP, exist_ok=True)


    # nome do arquivo com data e hora
    data = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    destino = f"{PASTA_BACKUP}/banco_{data}.db"


    # backup seguro usando o próprio SQLite
    origem = sqlite3.connect(BANCO)

    destino_db = sqlite3.connect(destino)

    with destino_db:
        origem.backup(destino_db)


    destino_db.close()
    origem.close()


    # registra no log do sistema
    conn = sqlite3.connect(BANCO)

    cursor = conn.cursor()

  # registra na auditoria
    conn = sqlite3.connect(BANCO)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO auditoria
        (
            usuario,
            usuario_id,
            acao,
            descricao
        )
        VALUES (?, ?, ?, ?)
    """,
    (
        usuario,
        None,
        "BACKUP",
        f"Backup criado: {destino}"
    ))

    conn.commit()
    conn.close()

    limpar_backups()
    return destino


def limpar_backups(maximo=30):

    if not os.path.exists(PASTA_BACKUP):
        return


    arquivos = []

    for arquivo in os.listdir(PASTA_BACKUP):

        caminho = os.path.join(PASTA_BACKUP, arquivo)

        if os.path.isfile(caminho) and arquivo.endswith(".db"):
            arquivos.append(caminho)


    # ordena do mais antigo para o mais novo
    arquivos.sort(key=os.path.getctime)


    while len(arquivos) > maximo:

        remover = arquivos.pop(0)

        os.remove(remover)