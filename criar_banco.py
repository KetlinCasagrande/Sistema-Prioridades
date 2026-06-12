import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

# =========================
# USUÁRIOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE,
    senha TEXT,
    tipo TEXT
)
""")
# =========================
# TERMOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS termos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT NOT NULL,
    cpf TEXT NOT NULL,
    rg TEXT,
    profissao TEXT,
    endereco TEXT,
    numero TEXT,
    complemento TEXT,
    cidade TEXT,
    estado TEXT,

    valor_total REAL NOT NULL,
    valor_extenso TEXT,

    usuario_id INTEGER,
    usuario_nome TEXT,

    data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,

    texto_final TEXT,
    pdf_path TEXT
)
""")

# =========================
# CONTRATOS DOS TERMOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS termos_contratos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    termo_id INTEGER NOT NULL,

    banco TEXT NOT NULL,
    contrato TEXT NOT NULL,
    data_contratacao TEXT,
    saldo REAL NOT NULL,

    FOREIGN KEY (termo_id)
    REFERENCES termos(id)
)
""")

# =========================
# AVISOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    mensagem TEXT
)
""")

# =========================
# COMISSÕES (NOVA E LIMPA)
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS comissoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco TEXT,
    produto TEXT,
    tabela_nome TEXT,
    comissao REAL,
    prazo TEXT,
    score REAL,
    promotora TEXT,
    ativo INTEGER DEFAULT 1
)
""")


conn.commit()
conn.close()

print("✔ Banco recriado com sucesso!")

