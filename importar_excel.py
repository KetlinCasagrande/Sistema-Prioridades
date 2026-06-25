import sqlite3
from datetime import datetime
import pandas as pd

DB = "banco.db"
ARQUIVO = r"D:\Sistema Prioridades\excel\comissoes.xlsx"


def conectar():
    return sqlite3.connect(DB)


def normalizar_produto(nome):
    if not nome:
        return ""

    nome = str(nome).strip().upper()

    if nome in ["COMPRA DÍVIDA", "COMPRA DIVIDA"]:
        return "COMPRA_DIVIDA"

    return nome


def tratar_comissao(valor):
    try:

        if pd.isna(valor):
            return 0

        valor = str(valor).strip()

        valor = valor.replace("%", "")
        valor = valor.replace(",", ".")

        return round(float(valor), 2)

    except:
        return 0

def normalizar_banco(nome):
    if not nome:
        return ""

    nome = str(nome).strip()

    # remove espaços duplicados
    nome = " ".join(nome.split())

    # padroniza tudo em maiúsculo
    nome = nome.upper()

    # correções específicas
    mapa = {
        "FACTA FINANCEIRA": "FACTA",
        "FACTA FINANCEIRA S.A": "FACTA",
        "FACTA S.A": "FACTA",
        "BANCO FACTA": "FACTA",

        "BMG CARD": "BMG",
        "BANCO BMG": "BMG",

        "AGIBANK": "AGIBANK",
        "AGI": "AGIBANK",

        "DAYCOVAL": "DAYCOVAL",
        "BANCO DAYCOVAL": "DAYCOVAL",


        "TOTALCASH": "TOTALCASH",
        "TOTAL": "TOTALCASH",
        "TOTAL CASH": "TOTALCASH",

        "QUALIBANKING": "QUALIBANKING",
        "QUALI BANKING": "QUALIBANKING",
        "QUALI": "QUALIBANKING",

        "HAPPY": "HAPPY",
        "Happy": "HAPPY",

        "PICPAY": "PICPAY",
        "PICPAY BANK": "PICPAY",
        "BANCO PICPAY": "PICPAY",
        "PICPAY BANK S.A": "PICPAY",




    }

    return mapa.get(nome, nome)

def garantir_coluna_data_importacao():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(comissoes)")
    colunas = [col[1] for col in cursor.fetchall()]

    if "data_importacao" not in colunas:
        print("➕ Criando coluna data_importacao...")
        cursor.execute("""
            ALTER TABLE comissoes
            ADD COLUMN data_importacao TEXT
        """)

    conn.commit()
    conn.close()


def normalizar_promotora(nome):
    if not nome:
        return ""

    nome = str(nome).strip()
    nome = " ".join(nome.split())
    nome = nome.upper()

    mapa = {
        "CONSIGA": "Consiga",
        "CRED FRANCO": "Credfranco",
        "CREDFRANCO": "Credfranco",
        "BEVICRED": "Bevicred",
        "CONECT": "Conect",
        "CONNECT": "Conect",
    }

    return mapa.get(nome, nome.title())


def importar_aba(sheet_name, data_importacao):
    print(f"📥 Importando aba: {sheet_name}")

    df = pd.read_excel(ARQUIVO, sheet_name=sheet_name)

    conn = conectar()
    cursor = conn.cursor()

    total_importados = 0

    for _, row in df.iterrows():

        banco = normalizar_banco(row.get("Banco", ""))
        tabela = str(row.get("Tabela", "")).strip()
        comissao = tratar_comissao(row.get("Comissão", 0))
        promotora = normalizar_promotora(row.get("Promotora", ""))
        prazo = str(row.get("Prazo", "")).strip()
        produto = normalizar_produto(sheet_name)

        if not banco or banco.lower() == "nan":
            continue

        cursor.execute("""
            INSERT INTO comissoes (
                banco,
                produto,
                tabela_nome,
                comissao,
                prazo,
                promotora,
                ativo,
                data_importacao
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
        """, (
            banco,
            produto,
            tabela,
            comissao,
            prazo,
            promotora,
            data_importacao
        ))

        total_importados += 1

    conn.commit()
    conn.close()

    print(f"✔ Aba {sheet_name} importada com sucesso: {total_importados} registros")





if __name__ == "__main__":

    data_importacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    print("🚀 INICIANDO IMPORTAÇÃO")
    print(f"📅 Data da importação: {data_importacao}")

    garantir_coluna_data_importacao()

   

    importar_aba("CLT", data_importacao)
    importar_aba("INSS", data_importacao)
    importar_aba("FGTS", data_importacao)
    importar_aba("COMPRA DÍVIDA", data_importacao)

    print("✅ IMPORTAÇÃO FINALIZADA")