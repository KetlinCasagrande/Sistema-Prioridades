import sqlite3

conn = sqlite3.connect("banco.db")
cursor = conn.cursor()

# =========================
# TABELA USUÁRIOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    senha TEXT,
    tipo TEXT
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    usuario_id INTEGER,
    acao TEXT,
    descricao TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS termos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente TEXT,
    cpf TEXT,
    valor_total REAL,
    usuario TEXT,
    html_termo TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")


# =========================
# TABELA COMISSÕES
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS comissoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco TEXT,
    tabela_nome TEXT,
    produto TEXT,
    comissao TEXT,
    prazo TEXT,
    promotora TEXT,
    status TEXT,
    ativo INTEGER DEFAULT 1
)
""")

# =========================
# TABELA AVISOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS avisos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    mensagem TEXT,
    criado_em TEXT
)
""")

cursor.execute("PRAGMA table_info(avisos)")
colunas_avisos = [coluna[1] for coluna in cursor.fetchall()]

if "criado_em" not in colunas_avisos:
    cursor.execute("""
        ALTER TABLE avisos
        ADD COLUMN criado_em TEXT
    """)

conn.commit()
# =========================
# TABELA BANCOS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS vendas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    produto TEXT,
    valor REAL,
    data TEXT DEFAULT CURRENT_DATE
)
""")


# META POR PRODUTO (NOVO)
cursor.execute("""
CREATE TABLE IF NOT EXISTS meta_produto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    produto TEXT UNIQUE,
    meta REAL DEFAULT 0
)
""")

# META POR USUÁRIO (NOVO)
cursor.execute("""
CREATE TABLE IF NOT EXISTS meta_usuario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    meta_total REAL DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS acessos_banco (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banco_id INTEGER,
    descricao TEXT,
    login TEXT,
    senha TEXT
)
""")

# =========================
# PLANILHA DE VENDAS
# =========================
cursor.execute("""
CREATE TABLE IF NOT EXISTS meta_usuario_produto (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER,
    produto TEXT,
    meta REAL DEFAULT 0,
    pago REAL DEFAULT 0,
    projecao REAL DEFAULT 0
)
""")


cursor.execute("""
CREATE TABLE IF NOT EXISTS status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT NOT NULL,
    acao TEXT NOT NULL,
    detalhes TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT,
    acao TEXT,
    detalhes TEXT,
    data_hora DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")



conn.commit()
conn.close()

print("✔ banco.db criado")
