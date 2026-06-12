import sqlite3
import pandas as pd

DB = "banco.db"
ARQUIVO = "D:\Sistema Prioridades\excel\comissoes.xlsx"  # <- coloque seu excel aqui


def conectar():
    conn = sqlite3.connect(DB)
    return conn


def normalizar_produto(nome):
    if not nome:
        return nome

    nome = str(nome).strip().upper()

    if nome in ["COMPRA DÍVIDA", "COMPRA DIVIDA"]:
        return "COMPRA_DIVIDA"

    return nome


def importar_aba(sheet_name):
    print(f"📥 Importando aba: {sheet_name}")

    df = pd.read_excel(ARQUIVO, sheet_name=sheet_name)

    conn = conectar()
    cursor = conn.cursor()

    for _, row in df.iterrows():

        banco = str(row.get("Banco", "")).strip()
        tabela = str(row.get("Tabela", "")).strip()
        comissao = row.get("Comissão", 0)
        promotora = str(row.get("Promotora", "")).strip()
        prazo = str(row.get("Prazo", "")).strip()

        produto = normalizar_produto(sheet_name)

        if not banco:
            continue

        cursor.execute("""
            INSERT INTO comissoes (
                banco,
                produto,
                tabela_nome,
                comissao,
                prazo,
                promotora,
                ativo
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            banco,
            produto,
            tabela,
            comissao,
            prazo,
            promotora
        ))

    conn.commit()
    conn.close()

    print(f"✔ Aba {sheet_name} importada com sucesso")


def limpar_dados():
    conn = conectar()
    cursor = conn.cursor()

    print("🧹 Limpando dados antigos...")

    cursor.execute("DELETE FROM comissoes")

    conn.commit()
    conn.close()


if __name__ == "__main__":

    # 🔥 OPÇÃO SEGURA (recomendado pra você agora)
    limpar_dados()

    importar_aba("CLT")
    importar_aba("INSS")
    importar_aba("FGTS")
    importar_aba("COMPRA DÍVIDA")

    print("🚀 IMPORTAÇÃO FINALIZADA")