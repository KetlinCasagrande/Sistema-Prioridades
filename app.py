from flask import Flask, flash, render_template, url_for, request, redirect, session, g
import sqlite3
import bcrypt
from functools import wraps
import os
import shutil
import pandas as pd
import calendar
from datetime import date
from math import ceil
from num2words import num2words
from flask import send_file
import os
import resend
from datetime import datetime, timedelta
import random
from dotenv import load_dotenv
import secrets



load_dotenv()
resend.api_key = os.environ.get("RESEND_API_KEY") 

app = Flask(__name__)
app.secret_key = "123"
resend.api_key = os.getenv("RESEND_API_KEY")
def db():
    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    return conn

def tema_usuario():
    if "usuario_id" not in session:
        return "rose"

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT tema
        FROM usuarios
        WHERE id = ?
    """, (session["usuario_id"],))

    user = cursor.fetchone()
    conn.close()

    return user["tema"] if user and user["tema"] else "rose"

def converter_valor_brasileiro(valor):

    if valor is None:
        return 0.0

    if isinstance(valor, (int, float)):
        return float(valor)

    valor = str(valor).strip()

    if not valor:
        return 0.0

    valor = valor.replace("R$", "").replace(" ", "")

    # Formato brasileiro: 1.234,56 ou 31,40
    if "," in valor:
        valor = valor.replace(".", "")
        valor = valor.replace(",", ".")

    try:
        return float(valor)
    except:
        return 0.0

def fazer_backup(usuario="sistema"):
    os.makedirs("backups", exist_ok=True)

    data = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    destino = f"backups/banco_{data}.db"

    shutil.copy2("banco.db", destino)

    # registra no log
    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO logs (usuario, acao, detalhes)
        VALUES (?, ?, ?)
    """, (usuario, "BACKUP", destino))

    conn.commit()
    conn.close()

    return destino

def garantir_coluna_competencia_metas():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(meta_usuario_produto)")
    colunas = [col[1] for col in cursor.fetchall()]

    if "competencia" not in colunas:

        cursor.execute("""
            ALTER TABLE meta_usuario_produto
            ADD COLUMN competencia TEXT
        """)

        print("✅ Coluna competencia criada.")

    conn.commit()
    conn.close()
def criar_tabelas_compra_divida():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            usuario_nome TEXT,

            nome TEXT NOT NULL,
            cpf TEXT,
            telefone TEXT,

            parcela_nova REAL DEFAULT 0,
            coeficiente REAL DEFAULT 0,
            valor_liberado REAL DEFAULT 0,

            status TEXT DEFAULT 'EM ANDAMENTO',
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes_compra_dividas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,

            banco TEXT,
            contrato TEXT,
            data_contratacao TEXT,

            parcela REAL DEFAULT 0,
            saldo REAL DEFAULT 0,

            status_boleto TEXT DEFAULT 'AGUARDANDO',
            observacao TEXT,

            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (cliente_id)
            REFERENCES clientes_compra(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulacoes_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,

            parcela REAL DEFAULT 0,
            coeficiente REAL DEFAULT 0,
            valor_liberado REAL DEFAULT 0,

            ativo INTEGER DEFAULT 1,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (cliente_id)
            REFERENCES clientes_compra(id)
        )
    """)

    conn.commit()
    conn.close()

    print("✔ Tabelas de compra de dívida criadas.")


def atualizar_tabela_clientes_compra():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(clientes_compra)")
    colunas_existentes = [
        coluna[1]
        for coluna in cursor.fetchall()
    ]

    novas_colunas = {
        "rg": "TEXT",
        "profissao": "TEXT",
        "endereco": "TEXT",
        "numero": "TEXT",
        "bairro_complemento": "TEXT",
        "cidade": "TEXT DEFAULT 'Paraguaçu Paulista'",
        "estado": "TEXT DEFAULT 'SP'"
    }

    for nome_coluna, tipo_coluna in novas_colunas.items():

        if nome_coluna not in colunas_existentes:

            cursor.execute(
                f"""
                ALTER TABLE clientes_compra
                ADD COLUMN {nome_coluna} {tipo_coluna}
                """
            )

            print(
                f"Coluna adicionada em clientes_compra: "
                f"{nome_coluna}"
            )

    conn.commit()
    conn.close()


def mascarar_email(email):
    if not email or "@" not in email:
        return ""

    nome, dominio = email.split("@", 1)

    if len(nome) <= 2:
        nome_mascarado = nome[0] + "***"
    else:
        nome_mascarado = nome[:2] + "***"

    return nome_mascarado + "@" + dominio
def enviar_email_recuperacao(destino, nome, link):

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="
        margin:0;
        background:#f4f6fb;
        font-family:Arial,Helvetica,sans-serif;
    ">

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center" style="padding:40px;">

                <table width="600" cellpadding="0" cellspacing="0"
                       style="
                            background:#ffffff;
                            border-radius:18px;
                            overflow:hidden;
                            box-shadow:0 10px 30px rgba(0,0,0,.08);
                       ">

                    <tr>
                        <td align="center"
                            style="
                                background:#151b2d;
                                padding:35px;
                            ">

                            <img
                                src="https://i.imgur.com/5SMiY2D.png"
                                width="180">

                        </td>
                    </tr>

                    <tr>
                        <td style="padding:40px;">

                            <h2 style="margin-top:0;color:#1f2937;">
                                Recuperação de senha
                            </h2>

                            <p style="font-size:16px;color:#475569;">
                                Olá,
                                <strong>{nome}</strong>.
                            </p>

                            <p style="font-size:16px;color:#475569;line-height:1.8;">
                                Recebemos uma solicitação para redefinir sua senha.
                            </p>

                            <div style="text-align:center;margin:35px 0;">

                                <a href="{link}"
                                   style="
                                    display:inline-block;
                                    background:#7C3AED;
                                    color:white;
                                    padding:15px 30px;
                                    border-radius:12px;
                                    text-decoration:none;
                                    font-weight:bold;
                                    font-size:16px;
                                   ">

                                   Redefinir minha senha

                                </a>

                            </div>

                            <p style="color:#64748b;">
                                Este link expira em
                                <strong>10 minutos</strong>.
                            </p>

                            <hr style="margin:35px 0;border:none;border-top:1px solid #e5e7eb;">

                            <p style="font-size:13px;color:#94a3b8;">
                                Caso você não tenha solicitado esta alteração,
                                basta ignorar este e-mail.
                            </p>

                        </td>
                    </tr>

                    <tr>

                        <td align="center"
                            style="
                                background:#f8fafc;
                                padding:18px;
                                color:#64748b;
                                font-size:13px;
                            ">

                            © Grupo Hipercred • Sistema Interno

                        </td>

                    </tr>

                </table>

            </td>
        </tr>
    </table>

    </body>
    </html>
    """

    params = {
        "from": "Hipercred <onboarding@resend.dev>",
        "to": [destino],
        "subject": "Redefinição de senha - Grupo Hipercred",
        "html": html
    }

    return resend.Emails.send(params)


def criar_tabela_recuperacao_senha():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recuperacao_senha (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            expira_em TEXT NOT NULL,
            utilizado INTEGER DEFAULT 0,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    """)

    conn.commit()
    conn.close()






def limpar_backups_antigos(dias=30):
    pasta = "backups"

    if not os.path.exists(pasta):
        return

    limite = datetime.now() - timedelta(days=dias)

    for arquivo in os.listdir(pasta):
        caminho = os.path.join(pasta, arquivo)

        if os.path.isfile(caminho):
            data_modificacao = datetime.fromtimestamp(
                os.path.getmtime(caminho)
            )

            if data_modificacao < limite:
                os.remove(caminho)
                print(f"🗑️ Removido: {arquivo}")

def home():

    ranking = buscar_ranking()
    top3 = ranking[:3]

    return render_template("home.html", top3=top3)

def dias_uteis_mes(ano, mes):
    total_dias = calendar.monthrange(ano, mes)[1]
    
    dias_uteis = 0
    
    for dia in range(1, total_dias + 1):
        if date(ano, mes, dia).weekday() < 5:  # seg a sex
            dias_uteis += 1
    
    return dias_uteis
def valor_por_extenso(valor):
    return num2words(valor, lang='pt_BR', to='currency')

def dias_uteis_passados():
    hoje = date.today()
    
    dias = 0
    
    for dia in range(1, hoje.day + 1):
        if date(hoje.year, hoje.month, dia).weekday() < 5:
            dias += 1
    
    return dias
def projecao_inteligente(meta, pago, dias_passados, dias_uteis):

    if dias_passados <= 0:
        return 0

    media_diaria = pago / dias_passados

    # evita projeção distorcida no início do mês
    if dias_passados < 3:
        return round(pago, 2)

    return round(media_diaria * dias_uteis, 2)


def necessario_por_dia(meta, pago, dias_uteis, dias_passados):

    restantes = dias_uteis - dias_passados

    if restantes <= 0:
        return 0

    falta = meta - pago

    if falta <= 0:
        return 0

    return round(falta / restantes, 2)


def dias_uteis_restantes():

    hoje = date.today()
    total_dias = calendar.monthrange(hoje.year, hoje.month)[1]

    restantes = 0

    for dia in range(hoje.day, total_dias + 1):
        if date(hoje.year, hoje.month, dia).weekday() < 5:
            restantes += 1

    return restantes

def registrar_log(usuario, acao, detalhes=""):
    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO logs (usuario, acao, detalhes)
        VALUES (?, ?, ?)
    """, (usuario, acao, detalhes))

    conn.commit()
    conn.close()

def limpar_promotora(promotora):
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM comissoes
        WHERE promotora = ?
    """, (promotora,))

    removidas = cursor.rowcount

    conn.commit()
    conn.close()

    return removidas


def limpar_promotora_produto(promotora, produto):

    promotora = promotora.strip().upper()
    produto = produto.strip().upper()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM comissoes
        WHERE UPPER(TRIM(promotora)) = ?
        AND UPPER(TRIM(produto)) = ?
    """, (
        promotora,
        produto
    ))

    removidas = cursor.rowcount

    conn.commit()
    conn.close()

    return removidas



def status_meta(meta, projecao):

    if meta <= 0:
        return "⚪ Sem meta definida"

    if projecao >= meta:
        return "🟢 No ritmo / acima da meta"

    elif projecao >= meta * 0.8:
        return "🟡 Atenção"

    return "🔴 Abaixo da meta"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("banco.db")
        g.db.row_factory = sqlite3.Row
    return g.db
import sqlite3

def buscar_ranking():
    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            u.usuario,
            SUM(v.valor) as total
        FROM vendas v
        JOIN usuarios u ON u.id = v.usuario_id
        GROUP BY v.usuario_id
        ORDER BY total DESC
    """)

    ranking = cursor.fetchall()
    conn.close()

    return ranking

@app.context_processor
def variaveis_globais():
    return {
        "tema": tema_usuario()
    }


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# =========================
# CONEXÃO
# =========================
def conectar():

    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row

    return conn

def atualizar_tabela_avisos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(avisos)")
    colunas = [coluna[1] for coluna in cursor.fetchall()]

    print("COLUNAS DA TABELA AVISOS:", colunas)

    if "criado_em" not in colunas:

        cursor.execute("""
            ALTER TABLE avisos
            ADD COLUMN criado_em TEXT
        """)
    if "categoria" not in colunas:
        cursor.execute("""
            ALTER TABLE avisos
            ADD COLUMN categoria TEXT DEFAULT 'informativo'
        """)


        conn.commit()

        print("Coluna criado_em adicionada com sucesso.")

    conn.close()

def registrar_auditoria(acao, descricao):
    try:
        conn = conectar()
        cursor = conn.cursor()

        print("AUDITORIA CHAMADA:", acao, descricao)  # 🔥 teste

        cursor.execute("""
            INSERT INTO auditoria (
                usuario,
                usuario_id,
                acao,
                descricao
            )
            VALUES (?, ?, ?, ?)
        """, (
            session.get("usuario"),
            session.get("usuario_id"),
            acao,
            descricao
        ))

        conn.commit()
        conn.close()

        print("AUDITORIA SALVA")  # 🔥 teste

    except Exception as e:
        print("Erro auditoria:", e)


  
# =========================
# LOGIN CHECK
# =========================
def verificar_login():
    return "usuario" in session




def atualizar_tabela_comissoes():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(comissoes)")
    colunas_existentes = [
        coluna[1]
        for coluna in cursor.fetchall()
    ]

    novas_colunas = {
        "atualizado_em": "TEXT",
        "atualizado_por": "TEXT"
    }

    for nome_coluna, tipo_coluna in novas_colunas.items():

        if nome_coluna not in colunas_existentes:

            cursor.execute(
                f"""
                ALTER TABLE comissoes
                ADD COLUMN {nome_coluna} {tipo_coluna}
                """
            )

            print(
                f"Coluna adicionada em comissoes: {nome_coluna}"
            )

    conn.commit()
    conn.close()



# =========================
# DECORATORS
# =========================
def apenas_master(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if "usuario" not in session:
            return redirect("/")

        

        return f(*args, **kwargs)

    return wrapper


def apenas_admin(f):

    @wraps(f)
    def wrapper(*args, **kwargs):

        if "usuario" not in session:
            return redirect("/")

        if session.get("tipo") not in ["adm", "master"]:
            return redirect("/home")

        return f(*args, **kwargs)

    return wrapper


# =========================
# BUSCAR AVISOS
# =========================
def buscar_avisos():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM avisos
        ORDER BY id DESC
        LIMIT 5
    """)

    avisos = cursor.fetchall()

    conn.close()

    return avisos
# =========================
# LOGS
# =========================
@app.route("/status")
def status():

    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 📋 logs recentes
    cursor.execute("""
        SELECT * FROM logs
        ORDER BY id DESC
        LIMIT 50
    """)
    logs = cursor.fetchall()

    # 📊 vendas hoje
    cursor.execute("""
        SELECT COUNT(*) FROM vendas
        WHERE date(data) = date('now')
    """)
    vendas_hoje = cursor.fetchone()[0]

    # 📄 termos hoje
    cursor.execute("""
        SELECT COUNT(*) FROM termos_contratos
        WHERE date(data) = date('now')
    """)
    termos_hoje = cursor.fetchone()[0]

    # 👥 usuários
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    usuarios = cursor.fetchone()[0]

    # 🕒 última atividade
    cursor.execute("""
        SELECT data FROM logs
        ORDER BY id DESC
        LIMIT 1
    """)
    ultima = cursor.fetchone()
    ultima_atividade = ultima[0] if ultima else "—"

    conn.close()

    return render_template(
        "status.html",
        logs=logs,
        vendas_hoje=vendas_hoje,
        termos_hoje=termos_hoje,
        usuarios=usuarios,
        ultima_atividade=ultima_atividade
    )
# =========================
# LOGIN
# =========================

@app.route("/", methods=["GET", "POST"])
def login():

    erro = ""

    if request.method == "POST":

        cpf = request.form.get("cpf", "").strip()
        senha = request.form.get("senha", "").strip()

        cpf_limpo = "".join(filter(str.isdigit, cpf))

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM usuarios
            WHERE REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = ?
        """, (cpf_limpo,))

        user = cursor.fetchone()

        if user and user["ativo"] == 0:
            conn.close()
            erro = "Usuário inativo. Procure o administrador."

        elif user and bcrypt.checkpw(
            senha.encode(),
            user["senha"].encode()
        ):

            agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute("""
                UPDATE usuarios
                SET ultimo_login = ?
                WHERE id = ?
            """, (agora, user["id"]))

            conn.commit()
            conn.close()

            session["usuario"] = user["usuario"]
            session["tipo"] = user["tipo"]
            session["usuario_id"] = user["id"]
            session["tema"] = user["tema"] if "tema" in user.keys() and user["tema"] else "rose"

            return redirect("/home")

        else:
            conn.close()
            erro = "CPF ou senha inválidos"

    return render_template(
    "login.html",
    erro=erro,
    recuperacao=request.args.get("recuperacao")
)

@app.route("/salvar-tema", methods=["POST"])
def salvar_tema():

    if not verificar_login() or "usuario_id" not in session:
        return {"ok": False}, 401

    tema = request.form.get("tema", "rose")

    temas_validos = [
        "rose", "ruby", "ice", "graphite", "coffee",
        "midnight", "sage", "lavender", "amber",
        "ocean", "emerald", "purple", "gold"
    ]

    if tema not in temas_validos:
        return {"ok": False}, 400

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET tema = ?
        WHERE id = ?
    """, (tema, session["usuario_id"]))

    conn.commit()
    conn.close()

    session["tema"] = tema

    return {"ok": True, "tema": tema}

@app.route("/meta-teste")
def meta_teste():
    hoje = date.today()

    dias_uteis = dias_uteis_mes(hoje.year, hoje.month)
    dias_passados = dias_uteis_passados()

    meta = 5000
    pago = 3000

    projecao = projecao_inteligente(meta, pago, dias_passados, dias_uteis)
    necessario = necessario_por_dia(meta, pago, dias_uteis, dias_passados)
    status = status_meta(meta, projecao)

    return render_template(
        "meta.html",
        dias_uteis_mes=dias_uteis,
        dias_passados=dias_passados,
        dias_restantes=dias_uteis - dias_passados,
        meta=meta,
        pago=pago,
        projecao=projecao,
        necessario=necessario,
        status=status
    )
# =========================
# HOME
# =========================
def home_vendas():

    conn = conectar()
    cursor = conn.cursor()

    usuario_id = session["usuario_id"]
    competencia_atual = date.today().strftime("%Y-%m")

    # =========================
    # TEMA DO USUÁRIO
    # =========================
    cursor.execute("""
        SELECT tema
        FROM usuarios
        WHERE id = ?
    """, (usuario_id,))

    usuario_tema = cursor.fetchone()
    tema = usuario_tema["tema"] if usuario_tema and usuario_tema["tema"] else "rose"

    session["tema"] = tema

    # =========================
    # AVISOS
    # =========================
    cursor.execute("""
        SELECT *
        FROM avisos
        ORDER BY id DESC
        LIMIT 5
    """)
    avisos = cursor.fetchall()

    # =========================
    # METAS DO MÊS
    # =========================
    cursor.execute("""
        SELECT *
        FROM meta_usuario_produto
        WHERE usuario_id = ?
        AND competencia = ?
        ORDER BY produto
    """, (usuario_id, competencia_atual))
    metas = cursor.fetchall()

    # =========================
    # VENDAS DO MÊS
    # =========================
    cursor.execute("""
        SELECT
            UPPER(produto) AS produto,
            SUM(valor) AS total
        FROM vendas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        GROUP BY UPPER(produto)
    """, (usuario_id, competencia_atual))
    vendas_mes = cursor.fetchall()

    vendas_dict = {
        v["produto"]: float(v["total"] or 0)
        for v in vendas_mes
    }

    meta_total = sum(float(m["meta"] or 0) for m in metas)
    vendido_total = sum(vendas_dict.values())
    falta_total = max(0, meta_total - vendido_total)

    percentual = round((vendido_total / meta_total) * 100, 1) if meta_total > 0 else 0
    percentual_barra = min(percentual, 100)

    progresso_produtos = []

    for m in metas:
        produto = m["produto"]
        meta = float(m["meta"] or 0)
        vendido = float(vendas_dict.get(produto.upper(), 0))
        perc = round((vendido / meta) * 100, 1) if meta > 0 else 0

        progresso_produtos.append({
            "produto": produto,
            "meta": meta,
            "vendido": vendido,
            "falta": max(0, meta - vendido),
            "percentual": perc,
            "percentual_barra": min(perc, 100)
        })

    # =========================
    # CLIENTES COMPRA EM ANDAMENTO
    # =========================
    cursor.execute("""
        SELECT *
        FROM clientes_compra
        WHERE usuario_id = ?
        AND status NOT IN ('CONCLUÍDO', 'CANCELADO')
        ORDER BY id DESC
        LIMIT 6
    """, (usuario_id,))
    clientes_compra = cursor.fetchall()

    # =========================
    # RANKING VENDEDORAS
    # =========================
    cursor.execute("""
        SELECT
            u.id,
            u.usuario,
            COALESCE(SUM(v.valor), 0) AS total
        FROM usuarios u
        LEFT JOIN vendas v
            ON v.usuario_id = u.id
            AND strftime('%Y-%m', v.data) = ?
        WHERE LOWER(TRIM(u.tipo)) NOT IN ('master', 'adm', 'admin')
        GROUP BY u.id, u.usuario
        ORDER BY total DESC
    """, (competencia_atual,))

    ranking_vendedoras = cursor.fetchall()

    # =========================
    # MISSÃO DO DIA
    # =========================
    cursor.execute("""
        SELECT status, COUNT(*) as total
        FROM clientes_compra
        WHERE usuario_id = ?
        AND status NOT IN ('CONCLUÍDO', 'CANCELADO')
        GROUP BY status
    """, (usuario_id,))
    status_clientes = cursor.fetchall()

    missao_status = {
        s["status"]: s["total"]
        for s in status_clientes
    }

    dias_uteis = dias_uteis_mes(date.today().year, date.today().month)
    dias_passados = dias_uteis_passados()
    necessario = necessario_por_dia(meta_total, vendido_total, dias_uteis, dias_passados)

    conn.close()

    return render_template(
        "home_vendas.html",
        usuario=session["usuario"],
        tipo=session["tipo"],
        tema=tema,
        avisos=avisos,
        competencia_atual=competencia_atual,
        meta_total=meta_total,
        vendido_total=vendido_total,
        falta_total=falta_total,
        percentual=percentual,
        percentual_barra=percentual_barra,
        progresso_produtos=progresso_produtos,
        ranking_vendedoras=ranking_vendedoras,
        missao_status=missao_status,
        necessario=necessario,
        clientes_compra=clientes_compra
    )

@app.route("/home")
def home():

    if not verificar_login():
        return redirect("/")

    tipo_usuario = session.get("tipo", "").lower().strip()

    if tipo_usuario not in ["master", "adm", "admin"]:
        return home_vendas()

   
    conn = conectar()
    cursor = conn.cursor()

    # =========================
    # AVISOS
    # =========================
    cursor.execute("""
        SELECT *
        FROM avisos
        ORDER BY id DESC
    """)
    avisos = cursor.fetchall()

    # =========================
    # TOTAL BANCOS
    # =========================
    cursor.execute("""
        SELECT COUNT(DISTINCT banco) as total
        FROM comissoes
        WHERE ativo IS NULL OR ativo = 1
    """)
    total_bancos = cursor.fetchone()["total"]

    # =========================
    # METAS
    # =========================
    cursor.execute("""
        SELECT *
        FROM meta_produto
    """)
    metas = cursor.fetchall()

    # =========================
    # VENDAS DO USUÁRIO (CARD INDIVIDUAL)
    # =========================
    cursor.execute("""
        SELECT produto, SUM(valor) as total
        FROM vendas
        WHERE usuario_id = CAST(? AS INTEGER)
        GROUP BY produto
    """, (session["usuario_id"],))

    vendas_mes = cursor.fetchall()

    vendas_dict = {
    v["produto"].upper(): float(v["total"] or 0)
    for v in vendas_mes
}
    

    # =========================
    # 🏆 RANKING GLOBAL (TOP 3)
    # =========================
    cursor.execute("""
        SELECT 
            u.usuario,
            SUM(v.valor) as total
        FROM vendas v
        JOIN usuarios u ON u.id = v.usuario_id
        GROUP BY v.usuario_id
        ORDER BY total DESC
    """)

    ranking = cursor.fetchall()
    top3 = ranking[:3]

    # VENDAS HOJE
    cursor.execute("""
    SELECT COUNT(*) as total
    FROM vendas
    WHERE date(data) = date('now')
    """)
    vendas_hoje = cursor.fetchone()["total"]

# PRODUÇÃO DO MÊS
    cursor.execute("""
    SELECT SUM(valor) as total
    FROM vendas
    WHERE strftime('%Y-%m', data) = strftime('%Y-%m', 'now')
    """)
    producao_mes = cursor.fetchone()["total"] or 0

# TERMOS HOJE
    cursor.execute("""
    SELECT COUNT(*) as total
    FROM termos
    """)
    termos_hoje = cursor.fetchone()["total"]






    competencia_atual = date.today().strftime("%Y-%m")

    cursor.execute("""
        SELECT
            u.id,
            u.usuario,
            COALESCE(SUM(v.valor), 0) AS total
        FROM usuarios u
        LEFT JOIN vendas v
            ON v.usuario_id = u.id
            AND strftime('%Y-%m', v.data) = ?
        WHERE LOWER(TRIM(u.tipo)) NOT IN ('master', 'adm', 'admin')
        GROUP BY u.id, u.usuario
        ORDER BY total DESC
    """, (competencia_atual,))

    ranking_vendedoras = cursor.fetchall()


# USUÁRIOS

    cursor.execute("""
    SELECT COUNT(*) as total
    FROM usuarios
    """)
    
    usuarios_ativos = cursor.fetchone()["total"]

    cursor.execute("""
    SELECT *
    FROM logs
    ORDER BY id DESC
    LIMIT 5
    """)

    logs = cursor.fetchall()



    conn.close()
    

    return render_template(
        "home.html",
        avisos=avisos,
        total_bancos=total_bancos,
        metas=metas,
        vendas=vendas_dict,
        top3=top3,   # 🔥 AQUI ESTAVA FALTANDO
        tipo=session["tipo"],
        vendas_hoje=vendas_hoje,
        producao_mes=producao_mes,
        logs=logs,
        termos_hoje=termos_hoje,
        ranking_vendedoras=ranking_vendedoras,
        usuarios_ativos=usuarios_ativos,
        usuario=session["usuario"]
    )

@app.route("/dashboard")
def dashboard():
    db = get_db()

    usuario_id = session["usuario_id"]

    metas = db.execute("SELECT * FROM meta_produto").fetchall()

    vendas = db.execute("""
        SELECT produto, SUM(valor) as total
        FROM vendas
        WHERE usuario_id = CAST(? AS INTEGER)
        GROUP BY produto
    """, (usuario_id,)).fetchall()

    vendas_dict = {v["produto"]: v["total"] for v in vendas}

    return render_template("dashboard_vendas.html",
        metas=metas,
        vendas=vendas_dict
    )
# =========================
# LOGOUT
# =========================
@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# =========================
# BUSCAR PRIORIDADES
# =========================
def buscar_prioridades(produto):

    conn = conectar()
    cursor = conn.cursor()

    filtro_ativo = ""

    if session.get("tipo") not in ["master", "adm", "admin"]:
        filtro_ativo = "AND ativo = 1"

    cursor.execute(f"""
        SELECT 
            banco,
            MAX(CAST(REPLACE(comissao, ',', '.') AS REAL)) AS maior_comissao
        FROM comissoes
        WHERE produto = ?
        {filtro_ativo}
        GROUP BY banco
        ORDER BY maior_comissao DESC
    """, (produto,))

    bancos = cursor.fetchall()
    resultado = []

    for banco in bancos:

        cursor.execute(f"""
            SELECT *
            FROM comissoes
            WHERE produto = ?
            AND banco = ?
            {filtro_ativo}
            ORDER BY
            ativo DESC,
            CAST(REPLACE(comissao, ',', '.') AS REAL) DESC
        """, (
            produto,
            banco["banco"]
        ))

        tabelas = cursor.fetchall()
        tabelas_formatadas = []

        for t in tabelas:

            tabela_dict = dict(t)

            try:
                comissao = float(str(t["comissao"] or 0).replace(",", "."))
            except:
                comissao = 0

            if t["ativo"] == 0:
                status = "PAUSADA"

            elif tabela_dict.get("liberada", 0) == 1:
                status = "LIBERADA"

            elif produto == "CLT":
                status = "LIBERADA" if comissao >= 3.5 else "PRECISA_LIBERACAO"

            elif produto == "INSS":
                status = "LIBERADA" if comissao >= 7 else "PRECISA_LIBERACAO"

            elif produto == "FGTS":
                status = "LIBERADA" if comissao >= 10 else "PRECISA_LIBERACAO"

            elif produto == "COMPRA_DIVIDA":
                status = "LIBERADA" if comissao >= 7 else "PRECISA_LIBERACAO"

            else:
                status = "PAUSADA"

            tabela_dict["status"] = status
            tabelas_formatadas.append(tabela_dict)

        resultado.append({
            "nome": banco["banco"],
            "tabelas": tabelas_formatadas
        })

    conn.close()

    return resultado
# =========================
# FILTRO DE BUSCA
# =========================
def aplicar_filtro(bancos, q):

    if not q:
        return bancos

    q = q.lower().strip()

    bancos_filtrados = []

    for banco in bancos:

        tabelas_filtradas = []

        for t in banco["tabelas"]:

            banco_nome = banco["nome"] or ""
            promotora = t.get("promotora") or ""
            tabela_nome = t.get("tabela_nome") or ""
            comissao = str(t.get("comissao", ""))
            prazo = str(t.get("prazo", ""))

            if (
                q in banco_nome.lower()
                or q in promotora.lower()
                or q in tabela_nome.lower()
                or q in comissao.lower()
                or q in prazo.lower()
            ):
                tabelas_filtradas.append(t)

        if tabelas_filtradas:
            bancos_filtrados.append({
                "nome": banco["nome"],
                "tabelas": tabelas_filtradas
            })

    return bancos_filtrados

@app.route("/liberar-tabela/<int:id>")
@apenas_admin
def liberar_tabela(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE comissoes
        SET liberada = 1
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(request.referrer or "/admin")

# =========================
# PRODUTOS
# =========================
@app.route("/clt")
def clt():

    if not verificar_login():
        return redirect("/")

    bancos = buscar_prioridades("CLT")

    q = request.args.get("q")
    bancos = aplicar_filtro(bancos, q)

    return render_template(
    "produto.html",
    pagina_ativa="clt",
    bancos=bancos,
    titulo="clt",
    avisos=buscar_avisos(),
    tipo=session["tipo"]
    )


@app.route("/inss")
def inss():

    if not verificar_login():
        return redirect("/")

    bancos = buscar_prioridades("INSS")

    q = request.args.get("q")
    bancos = aplicar_filtro(bancos, q)

    return render_template(
    "produto.html",
    pagina_ativa="inss",
    bancos=bancos,
    titulo="INSS",
    avisos=buscar_avisos(),
    tipo=session["tipo"]
    )


@app.route("/fgts")
def fgts():

    if not verificar_login():
        return redirect("/")

    bancos = buscar_prioridades("FGTS")

    q = request.args.get("q")
    bancos = aplicar_filtro(bancos, q)

    return render_template(
        "produto.html",
        pagina_ativa="fgts",
        bancos=bancos,
        titulo="FGTS",
        avisos=buscar_avisos(),
        tipo=session["tipo"]
    )


@app.route("/compra-divida")
def compra_divida():

    if not verificar_login():
        return redirect("/")

    bancos = buscar_prioridades("COMPRA_DIVIDA")

    q = request.args.get("q")
    bancos = aplicar_filtro(bancos, q)

    return render_template(
        "produto.html",
        pagina_ativa="compra",
        bancos=bancos,
        titulo="Compra Dívida",
        avisos=buscar_avisos(),
        tipo=session["tipo"]
    )

@app.route("/admin")
@apenas_admin
def admin():

    conn = conectar()
    cursor = conn.cursor()
    aba = request.args.get("aba", "usuarios")

    # =========================
    # PAGINAÇÃO
    # =========================
    pagina = max(1, int(request.args.get("pagina", 1)))
    por_pagina = 50
    offset = (pagina - 1) * por_pagina

# =========================
# FILTROS
# =========================
    q = request.args.get("q", "").strip()
    banco = request.args.get("banco", "").strip()
    produto = request.args.get("produto", "").strip()

# Filtros das metas
    competencia_filtro = request.args.get("competencia", "").strip()
    usuario_filtro = request.args.get("usuario_id", "").strip()

    # =========================
    # ORDENAÇÃO
    # =========================
    ordenar = request.args.get("ordenar", "banco")
    direcao = request.args.get("direcao", "asc")

    # campos permitidos (SEGURANÇA)
    campos_validos = {
        "banco": "banco",
        "produto": "produto",
        "comissao": "CAST(REPLACE(comissao, ',', '.') AS REAL)"
    }

    campo = campos_validos.get(ordenar, "banco")
    ordem = "DESC" if direcao == "desc" else "ASC"

    # =========================
    # USUÁRIOS
    # =========================
    cursor.execute("""
        SELECT *
        FROM usuarios
        ORDER BY id DESC
    """)
    usuarios = cursor.fetchall()

    # =========================
    # AVISOS
    # =========================
    cursor.execute("""
        SELECT *
        FROM avisos
        ORDER BY id DESC
    """)
    avisos = cursor.fetchall()

    # =========================
    # LOGS
    # =========================
    cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()

    # =========================
    # VENDAS
    # =========================
    cursor.execute(
    "SELECT COUNT(*) FROM vendas WHERE date(data)=date('now')")
    vendas_hoje = cursor.fetchone()[0]

    # =========================
    # USUÁRIOS
    # =========================
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]

    # =========================
    # TERMOS
    # =========================
    cursor.execute("""
    SELECT COUNT(*)
    FROM logs
    WHERE acao = 'GEROU TERMO'
    AND date(data_hora)=date('now')
    """)
    termos_hoje = cursor.fetchone()[0]

    cursor.execute("PRAGMA table_info(logs)")
    print(cursor.fetchall())

    # =========================
    # BASE SQL (COMISSÕES)
    # =========================
    base_sql = """
        FROM comissoes
        WHERE 1=1
    """

    parametros = []
    parametros_count = []

    # =========================
    # FILTROS DINÂMICOS
    # =========================
    if q:
        filtro = """
            AND (
                banco LIKE ?
                OR produto LIKE ?
                OR promotora LIKE ?
                OR tabela_nome LIKE ?
            )
        """
        busca = f"%{q}%"
        base_sql += filtro
        parametros += [busca, busca, busca, busca]
        parametros_count += [busca, busca, busca, busca]

    if banco:
        base_sql += " AND banco = ? "
        parametros.append(banco)
        parametros_count.append(banco)

    if produto:
        base_sql += " AND produto = ? "
        parametros.append(produto)
        parametros_count.append(produto)

    # =========================
    # COUNT (PAGINAÇÃO)
    # =========================
    cursor.execute(
        "SELECT COUNT(*) " + base_sql,
        parametros_count
    )

    total_comissoes = cursor.fetchone()[0]
    total_paginas = ceil(total_comissoes / por_pagina) if total_comissoes > 0 else 1


    # =========================
    # statuss
    # =========================
    cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 50")
    logs = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) FROM vendas WHERE date(data)=date('now')")
    vendas_hoje = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cursor.fetchone()[0]
    cursor.execute("""
    SELECT COUNT(*)
    FROM logs
    WHERE acao = 'GEROU TERMO'
    """)
    termos_hoje = cursor.fetchone()[0]
    


    # =========================
    # LISTAS FILTRO (SELECTS)
    # =========================
    
    cursor.execute("""
        SELECT DISTINCT banco
        FROM comissoes
        ORDER BY banco
    """)
    lista_bancos = cursor.fetchall()

    cursor.execute("""
        SELECT DISTINCT produto
        FROM comissoes
        ORDER BY produto
    """)
    lista_produtos = cursor.fetchall()

    # =========================
    # COMISSÕES (LISTAGEM)
    # =========================
    comissoes = []

    if session.get("tipo") == "master":

        sql = """
            SELECT *
        """ + base_sql + f"""
            ORDER BY {campo} {ordem}
            LIMIT ?
            OFFSET ?
        """

        parametros_lista = parametros + [por_pagina, offset]

        cursor.execute(sql, parametros_lista)
        comissoes = cursor.fetchall()
        print("TOTAL LISTADO:", len(comissoes))
        if comissoes:
            print("PRIMEIRO ID:", comissoes[0]["id"])
            print("ULTIMO ID:", comissoes[-1]["id"])



    # =========================
    # METAS
    # =========================
    cursor.execute("""
        SELECT *
        FROM meta_produto
    """)
    metas = cursor.fetchall()

    sql_metas = """
    SELECT
        meta_usuario_produto.*,
        usuarios.usuario
    FROM meta_usuario_produto
    JOIN usuarios
        ON usuarios.id = meta_usuario_produto.usuario_id
    WHERE 1=1
"""

    params_metas = []

    if competencia_filtro:
        sql_metas += " AND meta_usuario_produto.competencia = ? "
        params_metas.append(competencia_filtro)

    if usuario_filtro:
        sql_metas += " AND meta_usuario_produto.usuario_id = ? "
        params_metas.append(usuario_filtro)

    sql_metas += """
        ORDER BY
            meta_usuario_produto.competencia DESC,
            usuarios.usuario ASC,
            meta_usuario_produto.produto ASC
    """

    cursor.execute(sql_metas, params_metas)
    metas_usuarios = cursor.fetchall()

    conn.close()

    return render_template(
        "admin.html",
        usuarios=usuarios,
        comissoes=comissoes,
        avisos=avisos,
        metas=metas,
        logs=logs,
        vendas_hoje=vendas_hoje,
        termos_hoje=termos_hoje,
        total_usuarios=total_usuarios,
        metas_usuarios=metas_usuarios,
        lista_bancos=lista_bancos,
        lista_produtos=lista_produtos,
        pagina=pagina,
        total_paginas=total_paginas,
        ordenar=ordenar,
        direcao=direcao,
        pagina_ativa=aba,
        competencia_filtro=competencia_filtro,
        usuario_filtro=usuario_filtro,
        tipo=session["tipo"]
    )

@app.route("/admin/meta-produto", methods=["POST"])
def update_meta_produto():
    db = get_db()

    produto = request.form["produto"]
    meta = request.form["meta"]

    db.execute("""
        UPDATE meta_produto
        SET meta = ?
        WHERE produto = ?
    """, (meta, produto))

    db.commit()
    return redirect("/admin")

@app.route("/admin/meta-usuario", methods=["POST"])
def update_meta_usuario():
    db = get_db()

    usuario_id = request.form["usuario_id"]
    meta_total = request.form["meta_total"]

    db.execute("""
        UPDATE meta_usuario
        SET meta_total = ?
        WHERE usuario_id = CAST(? AS INTEGER)
    """, (meta_total, usuario_id))

    db.commit()
    return redirect("/admin")

# =========================
# SALVAR META VENDEDORA
# =========================

@app.route("/teste-meta")
def teste_meta():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO meta_usuario_produto
        (usuario_id, produto, meta)
        VALUES (?, ?, ?)
    """, (3, "NOVO INSS", 30000))

    conn.commit()
    conn.close()

    return "META CRIADA"

@app.route("/ver-usuarios")
def ver_usuarios():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, usuario
        FROM usuarios
    """)

    usuarios = cursor.fetchall()

    conn.close()

    return str([dict(u) for u in usuarios])
@app.route("/admin/salvar-meta-vendedora", methods=["POST"])
@apenas_master
def salvar_meta_vendedora():

    conn = conectar()
    cursor = conn.cursor()

    id_meta = request.form.get("id")
    meta = request.form.get("meta", "0").replace(".", "").replace(",", ".")
    competencia = request.form.get("competencia", "")
    usuario_id = request.form.get("usuario_id", "")

    cursor.execute("""
        UPDATE meta_usuario_produto
        SET meta = ?
        WHERE id = ?
    """, (meta, id_meta))

    conn.commit()
    conn.close()

    return redirect(f"/admin?aba=metas&competencia={competencia}&usuario_id={usuario_id}")


# =========================
# USUÁRIOS
# =========================
@app.route("/admin/usuario/criar", methods=["POST"])
@apenas_admin
def criar_usuario():

    try:
        usuario = request.form.get("usuario", "").strip()
        cpf = request.form.get("cpf", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()
        tipo = request.form.get("tipo", "user").strip()

        if session.get("tipo") != "master":
                tipo = "user"

        senha_hash = bcrypt.hashpw(
            senha.encode(),
            bcrypt.gensalt()
        ).decode()

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO usuarios
            (usuario, cpf, email, senha, tipo, ativo)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            usuario,
            cpf,
            email,
            senha_hash,
            tipo,
            1
        ))

        conn.commit()
        conn.close()

        print("✔ USUÁRIO CRIADO:", usuario)

        return redirect("/admin?aba=usuarios")

    except Exception as e:
        print("❌ ERRO AO CRIAR USUÁRIO:", e)
        return redirect("/admin?aba=usuarios")

@app.route("/admin/usuario/editar/<int:id>", methods=["POST"])
@apenas_admin
def editar_usuario(id):

    usuario = request.form.get("usuario", "").strip()
    cpf = request.form.get("cpf", "").strip()
    email = request.form.get("email", "").strip()
    tipo = request.form.get("tipo", "user").strip()
    ativo = request.form.get("ativo", "1")
    nova_senha = request.form.get("nova_senha", "").strip()

    conn = conectar()
    cursor = conn.cursor()

    # Busca o usuário que está sendo alterado
    cursor.execute("""
        SELECT id, usuario, tipo
        FROM usuarios
        WHERE id = ?
    """, (id,))

    usuario_editado = cursor.fetchone()

    if not usuario_editado:
        conn.close()
        flash("Usuário não encontrado.", "error")
        return redirect("/admin?aba=usuarios")

    tipo_logado = session.get("tipo", "").lower().strip()
    tipo_atual_usuario = usuario_editado["tipo"].lower().strip()

    # Administrador não pode alterar usuário master
    if tipo_logado != "master" and tipo_atual_usuario == "master":
        conn.close()
        flash("Apenas o master pode alterar outro usuário master.", "error")
        return redirect("/admin?aba=usuarios")

    # Somente o master pode escolher o tipo do usuário
    if tipo_logado != "master":
        tipo = tipo_atual_usuario

    tipos_permitidos = ["user", "adm", "master"]

    if tipo not in tipos_permitidos:
        tipo = tipo_atual_usuario

    if ativo not in ["0", "1"]:
        ativo = "1"

    if not usuario:
        conn.close()
        flash("O nome do usuário é obrigatório.", "error")
        return redirect("/admin?aba=usuarios")

    # Caso tenha sido preenchida uma nova senha
    if nova_senha:

        if len(nova_senha) < 6:
            conn.close()
            flash("A nova senha deve ter pelo menos 6 caracteres.", "error")
            return redirect("/admin?aba=usuarios")

        senha_hash = bcrypt.hashpw(
            nova_senha.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        cursor.execute("""
            UPDATE usuarios
            SET usuario = ?,
                cpf = ?,
                email = ?,
                tipo = ?,
                ativo = ?,
                senha = ?
            WHERE id = ?
        """, (
            usuario,
            cpf,
            email,
            tipo,
            ativo,
            senha_hash,
            id
        ))

        descricao_auditoria = (
            f"Dados e senha do usuário {usuario} foram alterados"
        )

    else:

        cursor.execute("""
            UPDATE usuarios
            SET usuario = ?,
                cpf = ?,
                email = ?,
                tipo = ?,
                ativo = ?
            WHERE id = ?
        """, (
            usuario,
            cpf,
            email,
            tipo,
            ativo,
            id
        ))

        descricao_auditoria = (
            f"Dados do usuário {usuario} foram alterados"
        )

    conn.commit()
    conn.close()

    registrar_auditoria(
        "EDITAR_USUARIO",
        descricao_auditoria
    )

    flash("Usuário atualizado com sucesso!", "success")

    return redirect("/admin?aba=usuarios")

@app.route("/admin/usuario/deletar/<int:id>")
@apenas_admin
def deletar_usuario(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM usuarios
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/admin?aba=usuarios")
# =========================
# AVISOS
# =========================
@app.route("/admin/aviso/criar", methods=["POST"])
@apenas_admin
def criar_aviso():

    titulo = request.form["titulo"].strip()
    mensagem = request.form["mensagem"].strip()
    categoria = request.form.get("categoria", "informativo")

    criado_em = datetime.now().strftime("%d/%m/%Y às %H:%M")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO avisos
        (titulo, mensagem, criado_em, categoria)
        VALUES (?, ?, ?, ?)
    """, (
        titulo,
        mensagem,
        criado_em,
        categoria
    ))

    conn.commit()
    conn.close()

    return redirect("/admin?aba=avisos")

@app.route("/admin/aviso/deletar/<int:id>")
@apenas_admin
def deletar_aviso(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM avisos
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect("/admin?aba=avisos")

@app.route("/admin/aviso/editar/<int:id>", methods=["POST"])
@apenas_admin
def editar_aviso(id):

    titulo = request.form["titulo"].strip()
    mensagem = request.form["mensagem"].strip()
    categoria = request.form.get("categoria", "informativo")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE avisos
        SET titulo = ?,
            mensagem = ?,
            categoria = ?
        WHERE id = ?
    """, (
        titulo,
        mensagem,
        categoria,
        id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin?aba=avisos")

@app.route("/termos", methods=["GET", "POST"])
def termos():

   
    if request.method == "POST":
        # 1. Captura de dados do formulário
        cliente = request.form.get("cliente", "").strip()
        cpf = request.form.get("cpf", "").strip()
        rg = request.form.get("rg", "").strip()
        profissao = request.form.get("profissao", "").strip()
        endereco = request.form.get("endereco", "").strip()
        numero = request.form.get("numero", "").strip()
        complemento = request.form.get("complemento", "").strip()
        cidade = request.form.get("cidade", "Paraguaçu Paulista").strip()
        estado = request.form.get("estado", "SP").strip()
        parcelas = request.form.getlist("parcela[]")

        # Captura das listas dinâmicas
        bancos = request.form.getlist("banco[]")
        contratos = request.form.getlist("contrato[]")
        datas_contratacao = request.form.getlist("data_contratacao[]")
        saldos = request.form.getlist("saldo[]")

        # 2. Processamento dos contratos em tabela
        linhas_tabela = ""
        valor_total = 0.0
        total_parcelas = 0.0

        bancos_unicos = sorted(
            list(
                set([b for b in bancos if b])
            )
        )

        def moeda(valor):
            return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        for i in range(len(bancos)):

            if not bancos[i]:
                continue

            parcela_float = converter_valor_brasileiro(parcelas[i])
            saldo_float = converter_valor_brasileiro(saldos[i])

            total_parcelas += parcela_float
            valor_total += saldo_float

            linhas_tabela += f"""
<tr>
    <td style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;">
        {contratos[i]}
    </td>

    <td style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;">
        {bancos[i]}
    </td>

    <td style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;">
        R$ {moeda(parcela_float)}
    </td>

    <td style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;">
        R$ {moeda(saldo_float)}
    </td>
</tr>
"""
        tabela_contratos = f"""
<table class="tabela-contratos-termo" style="
width:100%;
margin:16px auto 20px auto;
border-collapse:collapse;
table-layout:fixed;
font-size:10pt;
background:#fff;
border:1px solid #000;
">
    <thead>
    <tr>
        <th style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;font-weight:bold;">
            Nº Contrato
        </th>

        <th style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;font-weight:bold;">
            Banco
        </th>

        <th style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;font-weight:bold;">
            Parcela
        </th>

        <th style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;font-weight:bold;">
            Valor
        </th>
    </tr>
</thead>

    <tbody>
        {linhas_tabela}

       <tr>
    <td colspan="2"
        style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;font-weight:bold;">
        TOTAL
    </td>

    <td
        style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;font-weight:bold;">
        R$ {moeda(total_parcelas)}
    </td>

    <td
        style="border:1px solid #000;background:#fff;color:#000;padding:6px;text-align:center;font-weight:bold;">
        R$ {moeda(valor_total)}
    </td>
</tr>
    </tbody>
</table>
"""

        valor_formatado = moeda(valor_total)
        valor_extenso = valor_por_extenso(valor_total)

        # 3. Data atual corrigida
        data_atual = datetime.now()
        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        data_hoje = f"{data_atual.day:02d} de {meses[data_atual.month - 1]} de {data_atual.year}"
        
        # Define as variáveis que faltavam para o HTML
        data_extenso_hoje = data_hoje
        data_vencimento = data_hoje

        # 4. Compilação do HTML nativo interno do termo
        print("data_vencimento:", data_vencimento)
        
        registrar_log(
            session["usuario"],
            "GEROU TERMO",
            cliente)
        
        texto_termo = f"""
    <div class="conteudo-word">

    <style>
    .tabela-contratos-termo{{
        width:88% !important;
        margin:16px auto 24px auto !important;
        border-collapse:collapse !important;
        table-layout:auto !important;
        background:#fff !important;
    }}

    .tabela-contratos-termo th,
    .tabela-contratos-termo td{{
        border:1px solid #000 !important;
        background:#fff !important;
        color:#000 !important;
        padding:5px 8px !important;
        font-size:9pt !important;
        line-height:1.2 !important;
        text-align:center !important;
        vertical-align:middle !important;
    }}

    .tabela-contratos-termo th{{
        font-weight:bold !important;
    }}

    .tabela-contratos-termo .total{{
        font-weight:bold !important;
    }}
    </style>

            <h2 style="text-align:center; font-size: 14pt; margin-bottom: 24px; font-weight: bold;">INSTRUMENTO PARTICULAR DE CONFISSÃO DE DÍVIDA</h2>

            <p><i>Pelo presente instrumento particular e na melhor forma de direito, confessam e assumem como líquida e certa a obrigação a seguir descrita:</i></p>

            <p><b>CREDOR:</b> HIPERCRED INFORMAÇÕES CADASTRAIS LDTA, empresa de direito privado, inscrita no CNPJ: 21.589.560/0001-01, situada na rua Pedro de Toledo, nº 48, CEP: 19.700-045, Paraguaçu Paulista - São Paulo;</p>

            <p><b>DEVEDOR:</b> {cliente}, {profissao}, portador(a) da cédula de identidade RG {rg} e inscrito(a) CPF {cpf}, residente e domiciliado(a) na {endereco} n {numero}, {complemento}, {cidade}, {estado}.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA PRIMEIRA - DA DÍVIDA:</h3>
        <p>O DEVEDOR possui uma dívida decorrente das obrigações financeiras relacionadas a contratos anteriormente firmados, conforme tabela abaixo constando nome do banco, número do contrato, data de averbação, valor de parcela e saldo devedor de cada contrato</p>
{tabela_contratos}

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA SEGUNDA - DA FINALIDADE:</h3>
            <p>A presente operação tem por finalidade a QUITAÇÃO pelo CREDOR, dos créditos originalmente devidos pelo DEVEDOR ao {", ".join(bancos_unicos)}, conforme descritos na clausula primeira.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA TERCEIRA - DA CONFISSÃO DE DÍVIDA:</h3>
            <p>Ressalvadas quaisquer outras obrigações aqui não incluídas, pelo presente instrumento e na melhor forma de direito, o DEVEDOR CONFESSA DEVER AO CREDOR a quantia líquida, certa e exigível no valor de R$ <span class="realce">{valor_formatado} ({valor_extenso})</span>, por 1 (uma) Nota Promissória no mesmo valor, discriminada in anexo, emitidas por (Hipercred Informações Cadastrais Ltda).</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA QUARTA - DA COMPRA DE DIVÍDA:</h3>
            <p>O DEVEDOR declara estar ciente de que a compra da dívida foi realizada com o objetivo de QUITAR as obrigações financeiras em face do {", ".join(bancos_unicos)}, contratada por ele, possibilitando melhores condições de abertura de novos créditos financeiros, portanto, sem qualquer vício de consentimento.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA QUINTA - DO PAGAMENTO:</h3>
            <p>O CREDOR assumi o pagamento integral da dívida acima descrita, podendo negociar da melhor forma e realizar a quitação diretamente ao banco e o DEVEDOR obriga-se a pagar a dívida na forma e prazo estipulados na Nota Promissória em anexo, em uma única parcela, que integra este instrumento para todos os fins de direito ao CREDOR.</p>

            <p><b>Parágrafo Único:</b> O não pagamento de qualquer parcela no seu vencimento, importará no vencimento integral e antecipado do débito, sujeitando o DEVEDOR, além da execução do presente instrumento, ao pagamento do valor integral do débito, sobre o qual incidirá a aplicação de multa de 10%, juros de mora de 1% ao mês e correção monetária, mais custas processuais e honorários advocatícios no importe de 20% sobre o valor total do débito.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA SEXTA - DO TÍTULO EXECUTIVO EXTRAJUDICIAL:</h3>
            <p>À DÍVIDA ora reconhecida e assumida pelo DEVEDOR, como líquida, certa e exigível, no valor mencionado na clausula primeira, aplica-se o disposto no artigo 784, I, do Novo Código de Processo Civil Brasileiro, haja vista o caráter de título executivo extrajudicial do presente instrumento de confissão de dívida.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA SÉTIMA - DA TOLERÂNCIA:</h3>
            <p>A eventual tolerância à infringência de qualquer das cláusulas deste instrumento ou o não exercício de qualquer direito nele previsto constituirá mera liberalidade, não implicando em novação ou transação de qualquer espécie.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA OITAVA - DA LIVRE MANIFESTAÇÃO DE VONTADE:</h3>
            <p>O DEVEDOR declara, de forma expressa, que celebra o presente instrumento de confissão de dívida por sua livre e espontânea vontade, estando plenamente ciente de todas as condições aqui pactuadas.</p>

            <p>Declara, ainda, que:</p>
            <p>a) não sofreu qualquer tipo de coação, ameaça, dolo ou constrangimento para a assinatura deste instrumento;<br>
            b) teve pleno conhecimento e compreensão de todas as cláusulas e efeitos jurídicos decorrentes deste ajuste;<br>
            c) assinou o presente contrato em caráter irrevogável e irretratável, reconhecendo sua validade e eficácia.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA NONA - DO FORO:</h3>
            <p>Para dirimir qualquer dúvida oriunda deste instrumento fica eleito o Foro de Paraguaçu Paulista, estado do São Paulo, com exclusão de qualquer outro que seja.</p>

            <h3 style="font-size: 12pt; font-weight: bold; margin-top: 18px; margin-bottom: 6px;">CLÁUSULA DÉCIMA - DA DECLARAÇÃO DAS TESTEMUNHAS:</h3>
            <p>
As testemunhas abaixo assinadas declaram, sob as penas da lei,
que presenciaram a leitura e a assinatura do presente instrumento
pelas partes, atestando que o mesmo foi celebrado de forma livre,
consciente e sem qualquer indício de coação, fraude ou simulação.
</p>

            <p><b>PARAGRAFO PRIMEIRO:</b> As testemunhas afirmam, ainda, que têm pleno conhecimento do conteúdo do presente contrato e que poderão ser chamadas a confirmar sua autenticidade e veracidade, se necessário, em eventual processo judicial.</p>

            <p>Isto posto, firma este instrumento em 2 (duas) vias de igual teor, na presença de duas testemunhas.</p>

            <br>
            <p>Paraguaçu Paulista, {data_extenso_hoje}.</p>
            <br>

           <table style="width:100%; border:none; font-size:12pt; margin-top:60px;">
    <tr>
        <td style="width:45%; text-align:center; vertical-align:top;">
            _____________________________________<br><br>
            <b>CREDORA</b><br>
            HIPERCRED INFORMAÇÕES<br>
            CADASTRAIS LTDA
        </td>

        <td style="width:10%;"></td>

        <td style="width:45%; text-align:center; vertical-align:top;">
            _____________________________________<br><br>
            <b>DEVEDOR(A)</b><br>
            {cliente}
        </td>
    </tr>

    <tr>
        <td colspan="3" style="height:120px;"></td>
    </tr>

    <tr>
        <td style="width:45%; text-align:left; padding-left:40px;">
            _____________________________________<br><br>
            <b>TESTEMUNHA 1</b><br>
            Nome: ______________________________<br>
            
            CPF: _______________________________
        </td>

        <td style="width:10%;"></td>

        <td style="width:45%; text-align:left; padding-left:40px;">
            _____________________________________<br><br>
            <b>TESTEMUNHA 2</b><br>
            Nome: ______________________________<br>
            CPF: _______________________________
        </td>
    </tr>
</table>

            <div class="quebra-pagina"></div>

          <table class="tabela-promissoria">
    <tr>
        <td class="promissoria-conteudo">

            <h2 style="
                text-align:left;
                margin-top:0;
                margin-bottom:28px;
                font-weight:bold;
                font-size:15pt;
                color:#000 !important;">
                NOTA PROMISSÓRIA
            </h2>

            <table style="width:100%; border:none; margin-bottom:15px; font-size:10pt;">
                <tr>
                    <td style="width:45%; color:#000;">
                        <b>Nº</b> 01
                    </td>

                    <td style="width:55%; text-align:right; color:#000;">
                        <b>Vencimento:</b> {data_vencimento}
                    </td>
                </tr>

                <tr>
                    <td></td>

                    <td style="
                        text-align:right;
                        padding-top:5px;
                        font-size:14pt;
                        font-weight:bold;
                        color:#000;">
                        R$ {valor_formatado}
                    </td>
                </tr>
            </table>

            <p style="margin-top:10px; line-height:1.45; text-align:justify; color:#000;">
                No dia {data_vencimento}, eu <b>{cliente}</b>, pagarei por esta única via de
                <b>NOTA PROMISSÓRIA</b> na praça de Paraguaçu Paulista – Estado de São Paulo a:
                <b>HIPERCRED INFORMAÇÕES CADASTRAIS LTDA</b>, Inscrita no CNPJ N°:
                21.589.560/0001-01, à sua ordem a quantia
                <b>R$ {valor_formatado}</b> ({valor_extenso}) em moeda corrente deste país.
            </p>

            <p style="margin-top:10px; color:#000;">
                Emitida em: {data_extenso_hoje}
            </p>

            <p style="
                text-align:center;
                font-weight:bold;
                margin-top:25px;
                margin-bottom:25px;
                color:#000;">
                EMITENTE
            </p>

            <div style="text-align:center; color:#000; margin-top:10px;">
                ______________________________________________

                <br><br>

                <b>{cliente}</b>

                <br><br>

                <b>CPF:</b> {cpf}
            </div>

        </td>
    </tr>
</table>
        """
        conn = conectar()
        cursor = conn.cursor()
        cursor.execute("""
INSERT INTO termos (
cliente,
cpf,
rg,
profissao,
endereco,
numero,
complemento,
cidade,
estado,
valor_total,
valor_extenso,
usuario_nome,
usuario_id,
texto_final
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
cliente,
cpf,
rg,
profissao,
endereco,
numero,
complemento,
cidade,
estado,
valor_total,
valor_extenso,

session["usuario"],      # usuario_nome
session["usuario_id"],   # usuario_id

texto_termo

))
    
        print(session["usuario"])
        print(session["usuario_id"])
        print(session["tipo"])
        
        conn.commit()

        conn.close()


        registrar_auditoria(
            "GERAR_TERMO",
            f"Cliente: {cliente} | CPF: {cpf} | Valor: R$ {valor_total}"
        )
        return redirect("/termos/historico")
    # GET
    compra_id = request.args.get("compra_id")

    dados_compra = None
    contratos_compra = []

    if compra_id:
        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM clientes_compra
            WHERE id = ?
        """, (compra_id,))

        dados_compra = cursor.fetchone()

        cursor.execute("""
            SELECT *
            FROM clientes_compra_dividas
            WHERE cliente_id = ?
            ORDER BY id
        """, (compra_id,))

        contratos_compra = cursor.fetchall()

        conn.close()

    return render_template(
        "termos.html",
        texto_termo=None,
        tipo=session.get("tipo"),
        dados_compra=dados_compra,
        contratos_compra=contratos_compra
    )




# =========================
# COMISSÕES
# =========================
@app.route("/admin/comissao/criar", methods=["POST"])
@apenas_master
def criar_comissao():

    banco = request.form["banco"]
    produto = request.form["produto"]
    tabela_nome = request.form["tabela_nome"]
    comissao = request.form["comissao"]
    prazo = request.form["prazo"]
    status = request.form.get("status", "LIBERADA")
    
    promotora = request.form["promotora"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO comissoes
        (
            banco,
            produto,
            tabela_nome,
            comissao,
            prazo,
            promotora,
            status,
            ativo
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        banco,
        produto,
        tabela_nome,
        comissao,
        prazo,
        promotora,
        status
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/admin/comissao/editar/<int:id>", methods=["POST"])
@apenas_master
def editar_comissao(id):

    print("EDITANDO ID:", id)
    print("FORM RECEBIDO:", request.form)

    banco = request.form.get("banco")
    tabela_nome = request.form.get("tabela_nome")
    produto = request.form.get("produto")
    comissao = request.form.get("comissao")
    prazo = request.form.get("prazo")

    promotora = request.form.get("promotora")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE comissoes
        SET
            banco = ?,
            tabela_nome = ?,
            produto = ?,
            comissao = ?,
            prazo = ?,
            promotora = ?
        WHERE id = ?
    """, (
        banco,
        tabela_nome,
        produto,
        comissao,
        prazo,
        promotora,
        id
    ))

    conn.commit()
    conn.close()

    return redirect(request.referrer or "/admin")


@app.route("/auditoria")
def auditoria():

    if session.get("tipo") not in ["master", "admin", "adm"]:
        return redirect("/home")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM auditoria
        ORDER BY id DESC
        LIMIT 500
    """)

    registros = cursor.fetchall()

    conn.close()

    return render_template(
        "auditoria.html",
        pagina_ativa="auditoria",
        registros=registros,
        tipo=session.get("tipo")
        
    )

@app.route("/admin/comissao/deletar/<int:id>", methods=["POST"])
@apenas_master
def deletar_comissao(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM comissoes
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(request.referrer or "/admin")


# =========================
# TOGGLE TABELA
# =========================
@app.route("/toggle-tabela/<int:id>")
@apenas_master
def toggle_tabela(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ativo
        FROM comissoes
        WHERE id = ?
    """, (id,))

    atual = cursor.fetchone()

    if atual:

        novo = 0 if atual["ativo"] == 1 else 1

        cursor.execute("""
            UPDATE comissoes
            SET ativo = ?
            WHERE id = ?
        """, (
            novo,
            id
        ))

        conn.commit()

    conn.close()

    return redirect(request.referrer or "/admin")


# =========================
# DELETAR SELECIONADAS
# =========================
@app.route("/admin/comissao/deletar/selecionadas", methods=["POST"])
@apenas_master
def deletar_selecionadas():

    ids = request.form.getlist("ids")

    print("IDS:", ids)

    if not ids:
        return redirect(request.referrer or "/admin")

    try:
        ids = [int(i) for i in ids]
    except ValueError:
        return redirect(request.referrer or "/admin")

    conn = conectar()
    cursor = conn.cursor()

    placeholders = ",".join(["?"] * len(ids))

    cursor.execute(
        f"""
        DELETE FROM comissoes
        WHERE id IN ({placeholders})
        """,
        ids
    )

    print("ROWCOUNT:", cursor.rowcount)

    conn.commit()
    conn.close()

    return redirect(request.referrer or "/admin")
@app.route("/admin/meta/deletar/<int:id>")
@apenas_master
def deletar_meta(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT usuario_id, competencia
        FROM meta_usuario_produto
        WHERE id = ?
    """, (id,))

    meta = cursor.fetchone()

    usuario_id = meta["usuario_id"] if meta else ""
    competencia = meta["competencia"] if meta else ""

    cursor.execute("""
        DELETE FROM meta_usuario_produto
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(f"/admin?aba=metas&competencia={competencia}&usuario_id={usuario_id}")

# =========================
# IMPORTAR EXCEL
# =========================
@app.route("/admin/importar-excel", methods=["POST"])
@apenas_master
def importar_excel_painel():

    arquivo = request.files.get("arquivo")

    if not arquivo:
        return "Nenhum arquivo enviado"

    caminho = "comissoes.xlsx"
    arquivo.save(caminho)

    abas = pd.read_excel(caminho, sheet_name=None)

    conn = conectar()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    total_novos = 0
    total_atualizados = 0

    data_atualizacao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    usuario_atualizacao = session.get("usuario", "Sistema")

    for nome_aba, df in abas.items():

        produto_aba = nome_aba.strip().upper()

        # Normaliza os nomes das colunas
        df.columns = [c.strip().lower() for c in df.columns]

        for _, row in df.iterrows():

            banco = str(row.get("banco", "")).strip().upper()
            tabela_nome = str(row.get("tabela", "")).strip().upper()
            prazo = str(row.get("prazo", "")).strip().upper()
            promotora = str(row.get("promotora", "")).strip().upper()

            comissao = str(
                row.get("comissão", row.get("comissao", "0"))
            )

            comissao = comissao.replace(",", ".").strip()

            if not banco or not tabela_nome:
                continue

            cursor.execute("""
                SELECT id
                FROM comissoes
                WHERE banco = ?
                AND produto = ?
                AND tabela_nome = ?
                AND prazo = ?
                AND promotora = ?
            """, (
                banco,
                produto_aba,
                tabela_nome,
                prazo,
                promotora
            ))

            existe = cursor.fetchone()

            if existe:

                cursor.execute("""
                    UPDATE comissoes
                    SET
                        comissao = ?,
                        atualizado_em = ?,
                        atualizado_por = ?
                    WHERE id = ?
                """, (
                    comissao,
                    data_atualizacao,
                    usuario_atualizacao,
                    existe["id"]
                ))

                total_atualizados += 1

            else:

                cursor.execute("""
                    INSERT INTO comissoes (
                        banco,
                        produto,
                        tabela_nome,
                        comissao,
                        prazo,
                        promotora,
                        ativo,
                        atualizado_em,
                        atualizado_por
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (
                    banco,
                    produto_aba,
                    tabela_nome,
                    comissao,
                    prazo,
                    promotora,
                    data_atualizacao,
                    usuario_atualizacao
                ))

                total_novos += 1

    conn.commit()
    conn.close()

    registrar_auditoria(
        "IMPORTAR_COMISSOES",
        f"Novos: {total_novos} | Atualizados: {total_atualizados}"
    )

    return (
        f"✔ Importação concluída! "
        f"Novos: {total_novos} | "
        f"Atualizados: {total_atualizados}"
    )

@app.route("/termos/historico")
def historico():

    if "usuario_id" not in session:
        return redirect("/")

    pagina = request.args.get("pagina", 1, type=int)
    busca = request.args.get("busca", "").strip()
    busca_limpa = "".join(filter(str.isdigit, busca))

    por_pagina = 20
    offset = (pagina - 1) * por_pagina

    conn = conectar()
    cursor = conn.cursor()

    filtros = []
    params = []

    if session.get("tipo") not in ["master", "adm", "admin"]:
        filtros.append("usuario_id = ?")
        params.append(session["usuario_id"])

    if busca:
        filtros.append("""
            (
                cliente LIKE ?
                OR cpf LIKE ?
                OR REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') LIKE ?
            )
        """)
        params.extend([
            f"%{busca}%",
            f"%{busca}%",
            f"%{busca_limpa}%"
        ])

    where_sql = ""

    if filtros:
        where_sql = "WHERE " + " AND ".join(filtros)

    cursor.execute(f"""
        SELECT COUNT(*)
        FROM termos
        {where_sql}
    """, params)

    total = cursor.fetchone()[0]

    cursor.execute(f"""
        SELECT *
        FROM termos
        {where_sql}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
    """, params + [por_pagina, offset])

    historico_raw = cursor.fetchall()

    conn.close()

    historico = []

    for item in historico_raw:
        item = dict(item)

        try:
            item["valor_formatado"] = (
                f'{float(item["valor_total"]):,.2f}'
                .replace(",", "X")
                .replace(".", ",")
                .replace("X", ".")
            )
        except:
            item["valor_formatado"] = item["valor_total"]

        try:
            dt = datetime.strptime(item["data_criacao"], "%Y-%m-%d %H:%M:%S")
            item["data_formatada"] = dt.strftime("%d/%m/%Y")
            item["hora_formatada"] = dt.strftime("%H:%M")
        except:
            item["data_formatada"] = item["data_criacao"]
            item["hora_formatada"] = ""

        historico.append(item)

    total_paginas = ceil(total / por_pagina)

    return render_template(
        "historico.html",
        historico=historico,
        pagina=pagina,
        total_paginas=total_paginas,
        total=total,
        busca=busca,
        tipo=session.get("tipo")
    )

@app.route("/termos/excluir/<int:id>", methods=["POST"])
def excluir_termo(id):

    if session.get("tipo") != "master":
        return redirect("/home")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM termos WHERE id = ?",
        (id,)
    )

    conn.commit()
    conn.close()

    # 🔥 AUDITORIA AQUI
    registrar_auditoria(
        "EXCLUIR_TERMO",
        f"Termo ID {id} excluído"
    )

    return redirect("/termos/historico")

@app.route("/termos/ver/<int:id>")
def visualizar_termo(id):

    if "usuario_id" not in session:
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM termos
        WHERE id = ?
    """, (id,))

    termo = cursor.fetchone()

    conn.close()

    if not termo:
        return "Termo não encontrado"

    return render_template(
        "visualizar_termo.html",
        termo=termo
    )

@app.route("/backup")
def backup():

    usuario = session.get("usuario", "sistema")
    arquivo = fazer_backup(usuario)

    return f"✔ Backup criado com sucesso: {arquivo}"

@app.route("/bancos")
def bancos():

    if "usuario" not in session:
        return redirect("/")

    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    bancos = cursor.execute("""
        SELECT * FROM bancos
    """).fetchall()

    bancos_com_acessos = []

    for banco in bancos:

        acessos = cursor.execute("""
            SELECT * FROM acessos_banco
            WHERE banco_id = ?
        """, (banco["id"],)).fetchall()

        bancos_com_acessos.append({
            "id": banco["id"],
            "nome": banco["nome"],
            "link": banco["link"],
            "observacao": banco["observacao"],
            "acessos": acessos
        })

    conn.close()

    return render_template(
    "bancos.html",
    titulo="Bancos",
    bancos=bancos_com_acessos,
    usuario=session["usuario"],
    tipo=session["tipo"]
)
# =========================
# CRIAR ACESSO BANCO
# =========================
@app.route("/bancos/acesso/criar", methods=["POST"])
def criar_acesso_banco():

    if "usuario" not in session:
        return redirect("/")

    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO acessos_banco
        (banco_id, descricao, login, senha)
        VALUES (?, ?, ?, ?)
    """, (

        request.form["banco_id"],
        request.form["descricao"],
        request.form["login"],
        request.form["senha"]

    ))

    conn.commit()
    conn.close()

    return redirect("/bancos")


# =========================
# EDITAR ACESSO
# =========================
@app.route("/bancos/acesso/editar/<int:id>", methods=["POST"])
def editar_acesso_banco(id):

    if "usuario" not in session:
        return redirect("/")

    descricao = request.form.get("descricao", "").strip()
    login = request.form.get("login", "").strip()
    senha = request.form.get("senha", "").strip()

    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    if senha:
        cursor.execute("""
            UPDATE acessos_banco
            SET descricao = ?,
                login = ?,
                senha = ?
            WHERE id = ?
        """, (
            descricao,
            login,
            senha,
            id
        ))
    else:
        cursor.execute("""
            UPDATE acessos_banco
            SET descricao = ?,
                login = ?
            WHERE id = ?
        """, (
            descricao,
            login,
            id
        ))

    conn.commit()
    conn.close()

    return redirect("/bancos")

@app.route("/esqueci-senha", methods=["POST"])
def esqueci_senha():

    cpf = request.form.get("cpf", "").strip()
    cpf_limpo = "".join(filter(str.isdigit, cpf))

    mensagem_padrao = "Se existir um usuário ativo com esse CPF, enviaremos um link de recuperação para o e-mail cadastrado."

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM usuarios
        WHERE REPLACE(REPLACE(REPLACE(cpf, '.', ''), '-', ''), ' ', '') = ?
          AND ativo = 1
    """, (cpf_limpo,))

    user = cursor.fetchone()

    if user and user["email"]:

        token = secrets.token_urlsafe(48)

        expira_em = (
            datetime.now() + timedelta(minutes=10)
        ).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO recuperacao_senha
            (usuario_id, codigo, expira_em, utilizado)
            VALUES (?, ?, ?, 0)
        """, (
            user["id"],
            token,
            expira_em
        ))

        conn.commit()

        link = url_for(
            "redefinir_senha_token",
            token=token,
            _external=True
        )

        enviar_email_recuperacao(
            user["email"],
            user["usuario"],
            link
        )

    conn.close()

    return redirect("/?recuperacao=enviada")


@app.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha_token(token):

    erro = ""

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.*, u.usuario
        FROM recuperacao_senha r
        JOIN usuarios u ON u.id = r.usuario_id
        WHERE r.codigo = ?
          AND r.utilizado = 0
        ORDER BY r.id DESC
        LIMIT 1
    """, (token,))

    registro = cursor.fetchone()

    if not registro:
        conn.close()
        return redirect("/")

    expira_em = datetime.strptime(
        registro["expira_em"],
        "%Y-%m-%d %H:%M:%S"
    )

    if datetime.now() > expira_em:
        conn.close()
        return render_template(
            "redefinir_senha.html",
            erro="Link expirado. Solicite uma nova recuperação.",
            token=token
        )

    if request.method == "POST":

        senha = request.form.get("senha", "").strip()
        confirmar = request.form.get("confirmar", "").strip()

        if senha != confirmar:
            erro = "As senhas não conferem."

        elif len(senha) < 6:
            erro = "A senha deve ter pelo menos 6 caracteres."

        else:

            senha_hash = bcrypt.hashpw(
                senha.encode(),
                bcrypt.gensalt()
            ).decode()

            cursor.execute("""
                UPDATE usuarios
                SET senha = ?
                WHERE id = ?
            """, (
                senha_hash,
                registro["usuario_id"]
            ))

            # Invalida TODOS os links de recuperação desse usuário
            cursor.execute("""
                UPDATE recuperacao_senha
                SET utilizado = 1
                WHERE usuario_id = ?
            """, (
                registro["usuario_id"],
            ))

            conn.commit()
            conn.close()

            return render_template("senha_alterada.html")

    conn.close()

    return render_template(
        "redefinir_senha.html",
        erro=erro,
        token=token
    )
# =========================
# DELETAR ACESSO
# =========================
@app.route("/bancos/acesso/deletar/<int:id>")
def deletar_acesso_banco(id):

    if "usuario" not in session:
        return redirect("/")

    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM acessos_banco
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    registrar_auditoria(
        "DELETAR_ACESSO_BANCO",
        f"Acesso id {id} excluído"
    )

    return redirect("/bancos")

# =========================
# CRIAR BANCO
# =========================
@app.route("/bancos/criar", methods=["POST"])
def criar_banco():

    if "usuario" not in session:
        return redirect("/")

    nome = request.form.get("nome", "").strip().upper()
    link = request.form.get("link", "").strip()
    observacao = request.form.get("observacao", "").strip()

    if not nome:
        return redirect("/bancos")

    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO bancos (nome, link, observacao)
        VALUES (?, ?, ?)
    """, (nome, link, observacao))

    conn.commit()
    conn.close()

    registrar_auditoria(
        "CRIAR_BANCO",
        f"Banco {nome} cadastrado"
    )

    return redirect("/bancos")

@app.route("/bancos/excluir/<int:id>")
def excluir_banco(id):

    if "usuario" not in session:
        return redirect("/")

    if session.get("tipo", "").lower().strip() not in ["master", "admin", "adm"]:
        return redirect("/bancos")

    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Busca o nome do banco antes de excluir
    cursor.execute("""
        SELECT nome
        FROM bancos
        WHERE id = ?
    """, (id,))

    banco = cursor.fetchone()

    if not banco:
        conn.close()
        return redirect("/bancos")

    # Exclui os acessos vinculados
    cursor.execute("""
        DELETE FROM acessos_banco
        WHERE banco_id = ?
    """, (id,))

    # Exclui o banco
    cursor.execute("""
        DELETE FROM bancos
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    registrar_auditoria(
        "EXCLUIR_BANCO",
        f'Banco "{banco["nome"]}" excluído.'
    )

    return redirect("/bancos")


# =========================
# START
# =========================
@app.route("/salvar-venda", methods=["POST"])
def salvar_venda():

    if not verificar_login():
        return redirect("/")

    db = get_db()

    venda_id = request.form["id"]
    pago = request.form["pago"]
    projecao = request.form["projecao"]
    

    db.execute("""
        UPDATE meta_usuario_produto
        SET pago = ?, projecao = ?
        WHERE id = ?
    """, (pago, projecao, venda_id))

    

    db.commit()

    return redirect("/vendas")

@app.route("/vendas/add", methods=["POST"])
def add_venda():
    db = get_db()

    usuario_id = session["usuario_id"]
    produto = request.form["produto"]
    valor = request.form["valor"]
    cliente = request.form.get("cliente", "")

    db.execute("""
        INSERT INTO vendas (usuario_id, produto, valor)
        VALUES (?, ?, ?)
    """, (usuario_id, produto, valor))

    db.commit()

    detalhes = f"{produto} - R$ {valor}"

    if cliente:
        detalhes = f"{cliente} | {produto} - R$ {valor}"

    registrar_log(
        session["usuario"],
        "LANÇOU VENDA",
        detalhes
    )
    registrar_auditoria(
    "LANCOU_VENDA",
    f"{produto} | R$ {valor}"
    )

    return redirect("/vendas")

# =========================
# ADICIONAR META
# =========================
@app.route("/teste-session")
def teste_session():

    return str(session.get("usuario_id"))
@app.route("/ver-metas")
def ver_metas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM meta_usuario_produto
    """)

    metas = cursor.fetchall()

    conn.close()

    return str([dict(m) for m in metas])

@app.route("/admin/adicionar-meta", methods=["POST"])
@apenas_master
def adicionar_meta():

    conn = conectar()
    cursor = conn.cursor()

    usuario_id = request.form.get("usuario_id")
    produto = request.form.get("produto", "").strip().upper()
    meta = request.form.get("meta", "0").replace(".", "").replace(",", ".")
    competencia = request.form.get("competencia", "").strip()

    if not competencia:
        competencia = date.today().strftime("%Y-%m")

    cursor.execute("""
        INSERT INTO meta_usuario_produto
        (usuario_id, produto, meta, competencia)
        VALUES (?, ?, ?, ?)
    """, (usuario_id, produto, meta, competencia))

    conn.commit()
    conn.close()

    return redirect(f"/admin?aba=metas&competencia={competencia}&usuario_id={usuario_id}")
# =========================
# MINHAS VENDAS
# =========================
@app.route("/vendas")
def minhas_vendas():

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    # COMPETÊNCIA ATUAL
    competencia_atual = date.today().strftime("%Y-%m")

    # =========================
    # METAS DA VENDEDORA NO MÊS ATUAL
    # =========================
    cursor.execute("""
        SELECT *
        FROM meta_usuario_produto
        WHERE usuario_id = CAST(? AS INTEGER)
        AND competencia = ?
    """, (session["usuario_id"], competencia_atual))

    metas = cursor.fetchall()

    # =========================
    # VENDAS DO MÊS POR PRODUTO
    # =========================
    cursor.execute("""
        SELECT
            UPPER(produto) as produto,
            SUM(valor) as total
        FROM vendas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        GROUP BY UPPER(produto)
    """, (session["usuario_id"], competencia_atual))

    vendas_mes = cursor.fetchall()

    vendas_dict = {
        v["produto"]: float(v["total"] or 0)
        for v in vendas_mes
    }

    # =========================
    # HISTÓRICO DO MÊS ATUAL
    # =========================
    cursor.execute("""
        SELECT *
        FROM vendas
        WHERE usuario_id = ?
        AND strftime('%Y-%m', data) = ?
        ORDER BY id DESC
    """, (session["usuario_id"], competencia_atual))

    historico = cursor.fetchall()

    conn.close()

    # =========================
    # TOTAL META E TOTAL VENDIDO
    # =========================
    meta_total = sum(float(m["meta"] or 0) for m in metas)
    pago_total = sum(vendas_dict.values())
    falta_meta = max(0, meta_total - pago_total)

    # =========================
    # % GERAL
    # =========================
    percentual_meta = round((pago_total / meta_total) * 100, 1) if meta_total > 0 else 0
    percentual_barra = min(percentual_meta, 100)

    # =========================
    # PROGRESSO POR PRODUTO
    # =========================
    progresso_produtos = []

    for m in metas:

        produto = m["produto"].upper()
        meta = float(m["meta"] or 0)
        vendido = float(vendas_dict.get(produto, 0))

        percentual = round((vendido / meta) * 100, 1) if meta > 0 else 0
        percentual_barra = min(percentual, 100)

        progresso_produtos.append({
            "produto": produto,
            "meta": meta,
            "vendido": vendido,
            "percentual": percentual,
            "percentual_barra": percentual_barra,
            "falta": max(0, meta - vendido)
        })

    # =========================
    # INTELIGÊNCIA DO MÊS
    # =========================
    hoje = date.today()

    dias_uteis = dias_uteis_mes(hoje.year, hoje.month)
    dias_passados = dias_uteis_passados()

    projecao = projecao_inteligente(meta_total, pago_total, dias_passados, dias_uteis)
    necessario = necessario_por_dia(meta_total, pago_total, dias_uteis, dias_passados)
    status = status_meta(meta_total, projecao)

    return render_template(
        "vendas.html",
        metas=metas,
        vendas=vendas_dict,
        historico=historico,
        falta_meta=falta_meta,

        percentual_meta=percentual_meta,
        progresso_produtos=progresso_produtos,
        percentual_barra=percentual_barra,
        meta=meta_total,
        pago=pago_total,
        projecao=projecao,
        necessario=necessario,
        status=status,

        dias_uteis_mes=dias_uteis,
        dias_passados=dias_passados,
        dias_restantes=dias_uteis - dias_passados,

        competencia_atual=competencia_atual,

        tipo=session["tipo"],
        usuario=session["usuario"]
    )
@app.route("/admin/comissoes/limpar-promotora", methods=["POST"])
@apenas_master
def limpar_comissoes_promotora():

    promotora = request.form.get("promotora", "").strip()
    produto = request.form.get("produto", "").strip()

    if not promotora or not produto:
        flash(
            "Selecione a promotora e o produto antes de limpar.",
            "error"
        )

        return redirect("/admin?aba=comissoes")

    removidas = limpar_promotora_produto(
        promotora,
        produto
    )

    registrar_auditoria(
        "LIMPAR_PROMOTORA_PRODUTO",
        (
            f"Promotora: {promotora} | "
            f"Produto: {produto} | "
            f"Registros removidos: {removidas}"
        )
    )

    flash(
        (
            f"{removidas} comissões de {produto} da promotora "
            f"{promotora} foram removidas."
        ),
        "success"
    )

    return redirect(
        f"/admin?aba=comissoes"
        f"&promotora={promotora}"
        f"&produto={produto}"
    )

@app.route("/excluir-venda/<int:id>")
def excluir_venda(id):

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM vendas
        WHERE id = ?
        AND usuario_id = ?
    """, (
        id,
        session["usuario_id"]
    ))

    conn.commit()
    conn.close()

    registrar_log(
        session["usuario"],
        "EXCLUIU VENDA",
        f"Venda ID {id}"
    )
    registrar_auditoria(
    "EXCLUIU_VENDA",
    f"Venda ID {id}"
    )

    return redirect("/vendas")


@app.route("/editar-venda/<int:id>")
def editar_venda(id):

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM vendas
        WHERE id = ?
        AND usuario_id = ?
    """, (
        id,
        session["usuario_id"]
    ))

    venda = cursor.fetchone()

    conn.close()

    if not venda:
        return redirect("/vendas")

    registrar_log(
        session["usuario"],
        "ABRIU_EDICAO_VENDA",
        f"Venda ID {id}"
    )

    return render_template(
        "editar_venda.html",
        venda=venda
    )


@app.route("/editar-venda/<int:id>", methods=["POST"])
def salvar_edicao_venda(id):

    if not verificar_login():
        return redirect("/")

    valor = request.form["valor"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE vendas
        SET valor = ?
        WHERE id = ?
        AND usuario_id = ?
    """, (
        valor,
        id,
        session["usuario_id"]
    ))

    conn.commit()
    conn.close()

    registrar_log(
        session["usuario"],
        "SALVOU_EDICAO_VENDA",
        f"Venda ID {id} | Novo valor R$ {valor}"
    )
    registrar_auditoria(
    "EDITOU_VENDA",
    f"Venda ID {id} | Novo valor R$ {valor}"
    )

    return redirect("/vendas")

@app.route("/teste-soma")
def teste_soma():

    return f"""
    Usuario ID da sessão: {session.get('usuario_id')}
    """
@app.route("/todas-vendas")
def todas_vendas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM vendas
    """)

    dados = cursor.fetchall()

    conn.close()

    return str([dict(x) for x in dados])

@app.route("/compra-divida/cliente/editar/<int:id>", methods=["POST"])
def editar_cliente_compra(id):

    if not verificar_login():
        return redirect("/")

    nome = request.form.get("nome", "").strip()
    cpf = request.form.get("cpf", "").strip()
    telefone = request.form.get("telefone", "").strip()
    status = request.form.get("status", "EM ANDAMENTO").strip()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE clientes_compra
        SET
            nome = ?,
            cpf = ?,
            telefone = ?,
            status = ?
        WHERE id = ?
    """, (
        nome,
        cpf,
        telefone,
        status,
        id
    ))

    conn.commit()
    conn.close()

    return redirect(f"/compra-divida/cliente/{id}")




@app.route("/estrutura-vendas")
def estrutura_vendas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(vendas)")

    dados = cursor.fetchall()

    conn.close()

    return str([dict(x) for x in dados])

@app.route("/admin/comissoes/exportar")
@apenas_master
def exportar_comissoes():

    conn = conectar()

    df = pd.read_sql_query("""
        SELECT
            banco AS Banco,
            tabela_nome AS Tabela,
            produto AS Produto,
            prazo AS Prazo,
            comissao AS Comissão,
            promotora AS Promotora,
            ativo AS Ativo,
            data_importacao AS Atualização
        FROM comissoes
        ORDER BY produto, banco, CAST(REPLACE(comissao, ',', '.') AS REAL) DESC
    """, conn)

    conn.close()

    caminho = "comissoes_exportadas.xlsx"
    df.to_excel(caminho, index=False)

    return send_file(
        caminho,
        as_attachment=True,
        download_name="comissoes_exportadas.xlsx"
    )

def moeda_para_float(valor):
    if not valor:
        return 0

    valor = str(valor).strip()
    valor = valor.replace("R$", "").replace(" ", "")
    valor = valor.replace(".", "").replace(",", ".")

    try:
        return float(valor)
    except:
        return 0

@app.route("/compra-divida/clientes")
def compra_divida_clientes():

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()
    status = request.args.get("status", "ativos")

    base_sql = """
    SELECT
        c.*,
        u.usuario AS nome_criador,

        COALESCE((
            SELECT SUM(d.saldo)
            FROM clientes_compra_dividas d
            WHERE d.cliente_id = c.id
        ), 0) AS total_divida,

        COALESCE((
            SELECT s.valor_liberado
            FROM simulacoes_compra s
            WHERE s.cliente_id = c.id
            ORDER BY s.id DESC
            LIMIT 1
        ), 0) AS valor_liberado,

        (
            COALESCE((
                SELECT s.valor_liberado
                FROM simulacoes_compra s
                WHERE s.cliente_id = c.id
                ORDER BY s.id DESC
                LIMIT 1
            ), 0)
            -
            COALESCE((
                SELECT SUM(d.saldo)
                FROM clientes_compra_dividas d
                WHERE d.cliente_id = c.id
            ), 0)
        ) AS sobra

    FROM clientes_compra c

LEFT JOIN usuarios u
ON u.id = c.usuario_id



"""
    where = []
    params = []

    if status == "ativos":
        where.append("""
            c.status IN (
                'EM ANDAMENTO',
                'AGUARDANDO BOLETOS',
                'AGUARDANDO MARGEM',
                'AGUARDANDO RETORNO DA MARGEM'
            )
        """)

    elif status == "concluidos":
        where.append("c.status = 'CONCLUÍDO'")

    elif status == "cancelados":
        where.append("c.status = 'CANCELADO'")

# "todos" não adiciona filtro
    admin = session.get("tipo", "").lower().strip() in ["master", "adm", "admin"]

    if not admin:
        where.append("c.usuario_id = ?")
        params.append(session["usuario_id"])

    if where:
        base_sql += " WHERE " + " AND ".join(where)

    base_sql += " ORDER BY c.id DESC"

    cursor.execute(base_sql, params)

    clientes = cursor.fetchall()
    for c in clientes:
        print(dict(c))



    conn.close()

    return render_template(
        "compra_divida_clientes.html",
        clientes=clientes,
        tipo=session["tipo"],
        status=status,
        usuario=session["usuario"]
    )

@app.route("/compra-divida/clientes/criar", methods=["POST"])
def criar_cliente_compra():

    if not verificar_login():
        return redirect("/")

    nome = request.form.get("nome", "").strip()
    cpf = request.form.get("cpf", "").strip()
    rg = request.form.get("rg", "").strip()
    profissao = request.form.get("profissao", "").strip()

    endereco = request.form.get("endereco", "").strip()
    numero = request.form.get("numero", "").strip()
    bairro_complemento = request.form.get(
        "bairro_complemento", ""
    ).strip()

    cidade = request.form.get(
        "cidade",
        "Paraguaçu Paulista"
    ).strip()

    estado = request.form.get(
        "estado",
        "SP"
    ).strip().upper()

    if not nome:
        flash("Informe o nome do cliente.", "error")
        return redirect("/compra-divida/clientes")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO clientes_compra (
            usuario_id,
            usuario_nome,
            nome,
            cpf,
            rg,
            profissao,
            endereco,
            numero,
            bairro_complemento,
            cidade,
            estado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["usuario_id"],
        session["usuario"],
        nome,
        cpf,
        rg,
        profissao,
        endereco,
        numero,
        bairro_complemento,
        cidade or "Paraguaçu Paulista",
        estado or "SP"
    ))

    cliente_id = cursor.lastrowid

    conn.commit()
    conn.close()

    flash("Cliente criado com sucesso!", "success")

    return redirect(
        f"/compra-divida/cliente/{cliente_id}"
    )


@app.route("/compra-divida/cliente/<int:id>")
def abrir_cliente_compra(id):

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM clientes_compra
        WHERE id = ?
    """, (id,))
    cliente = cursor.fetchone()

    if not cliente:
        conn.close()
        return redirect("/compra-divida/clientes")

    if session.get("tipo", "").lower().strip() not in ["master", "admin", "adm"]:
        if cliente["usuario_id"] != session["usuario_id"]:
            conn.close()
            return redirect("/compra-divida/clientes")

    cursor.execute("""
        SELECT *
        FROM clientes_compra_dividas
        WHERE cliente_id = ?
        ORDER BY id DESC
    """, (id,))
    dividas = cursor.fetchall()

    cursor.execute("""
        SELECT *
        FROM simulacoes_compra
        WHERE cliente_id = ?
        ORDER BY id DESC
    """, (id,))
    simulacoes = cursor.fetchall()

    conn.close()

    total_parcelas = sum(float(d["parcela"] or 0) for d in dividas)
    total_dividas = sum(float(d["saldo"] or 0) for d in dividas)

    simulacao_principal = simulacoes[0] if simulacoes else None
    valor_liberado = float(simulacao_principal["valor_liberado"] or 0) if simulacao_principal else 0

    sobra = valor_liberado - total_dividas

    return render_template(
        "compra_divida_cliente.html",
        cliente=cliente,
        dividas=dividas,
        simulacoes=simulacoes,
        total_parcelas=total_parcelas,
        total_dividas=total_dividas,
        valor_liberado=valor_liberado,
        sobra=sobra,
        tipo=session["tipo"],
        usuario=session["usuario"]
    )


@app.route("/compra-divida/cliente/excluir/<int:id>")
def excluir_cliente_compra(id):

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    if session.get("tipo", "").lower().strip() not in ["master", "admin", "adm"]:
        cursor.execute("""
            SELECT usuario_id
            FROM clientes_compra
            WHERE id = ?
        """, (id,))
        cliente = cursor.fetchone()

        if not cliente or cliente["usuario_id"] != session["usuario_id"]:
            conn.close()
            return redirect("/compra-divida/clientes")

    cursor.execute("DELETE FROM clientes_compra_dividas WHERE cliente_id = ?", (id,))
    cursor.execute("DELETE FROM simulacoes_compra WHERE cliente_id = ?", (id,))
    cursor.execute("DELETE FROM clientes_compra WHERE id = ?", (id,))

    conn.commit()
    conn.close()

    return redirect("/compra-divida/clientes")


@app.route("/compra-divida/cliente/<int:cliente_id>/simulacao", methods=["POST"])
def adicionar_simulacao_compra(cliente_id):

    if not verificar_login():
        return redirect("/")

    parcela = converter_valor_brasileiro(request.form.get("parcela"))
    coeficiente = converter_valor_brasileiro(request.form.get("coeficiente"))

    valor_liberado = parcela / coeficiente if coeficiente > 0 else 0

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO simulacoes_compra (
            cliente_id,
            parcela,
            coeficiente,
            valor_liberado
        )
        VALUES (?, ?, ?, ?)
    """, (
        cliente_id,
        parcela,
        coeficiente,
        valor_liberado
    ))

    conn.commit()
    flash("Simulação criada com sucesso!", "success")

    print("SALVANDO SIMULAÇÃO", cliente_id, parcela, coeficiente, valor_liberado)
    conn.close()

    return redirect(f"/compra-divida/cliente/{cliente_id}")


@app.route("/compra-divida/simulacao/editar/<int:id>", methods=["POST"])
def editar_simulacao_compra(id):

    if not verificar_login():
        return redirect("/")

    parcela = converter_valor_brasileiro(request.form.get("parcela"))
    coeficiente = converter_valor_brasileiro(request.form.get("coeficiente"))

    valor_liberado = parcela / coeficiente if coeficiente > 0 else 0

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cliente_id
        FROM simulacoes_compra
        WHERE id = ?
    """, (id,))
    simulacao = cursor.fetchone()

    if not simulacao:
        conn.close()
        return redirect("/compra-divida/clientes")

    cliente_id = simulacao["cliente_id"]

    cursor.execute("""
        UPDATE simulacoes_compra
        SET parcela = ?,
            coeficiente = ?,
            valor_liberado = ?
        WHERE id = ?
    """, (
        parcela,
        coeficiente,
        valor_liberado,
        id
    ))

    conn.commit()
    conn.close()

    return redirect(f"/compra-divida/cliente/{cliente_id}")


@app.route("/compra-divida/simulacao/excluir/<int:id>")
def excluir_simulacao_compra(id):

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cliente_id
        FROM simulacoes_compra
        WHERE id = ?
    """, (id,))
    simulacao = cursor.fetchone()

    if not simulacao:
        conn.close()
        return redirect("/compra-divida/clientes")

    cliente_id = simulacao["cliente_id"]

    cursor.execute("""
        DELETE FROM simulacoes_compra
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(f"/compra-divida/cliente/{cliente_id}")


@app.route("/compra-divida/cliente/<int:id>/divida", methods=["POST"])
def adicionar_divida_compra(id):

    if not verificar_login():
        return redirect("/")

    banco = request.form.get("banco", "").strip()
    contrato = request.form.get("contrato", "").strip()
    data_contratacao = request.form.get("data_contratacao", "").strip()

    parcela = converter_valor_brasileiro(request.form.get("parcela"))
    saldo = converter_valor_brasileiro(request.form.get("saldo"))

    status_boleto = request.form.get("status_boleto", "AGUARDANDO")
    observacao = request.form.get("observacao", "").strip()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO clientes_compra_dividas (
            cliente_id,
            banco,
            contrato,
            data_contratacao,
            parcela,
            saldo,
            status_boleto,
            observacao
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id,
        banco,
        contrato,
        data_contratacao,
        parcela,
        saldo,
        status_boleto,
        observacao
    ))

    conn.commit()
    conn.close()

    return redirect(f"/compra-divida/cliente/{id}?aba=dividas")


@app.route("/compra-divida/divida/editar/<int:id>", methods=["POST"])
def editar_divida_compra(id):

    if not verificar_login():
        return redirect("/")

    banco = request.form.get("banco", "").strip()
    contrato = request.form.get("contrato", "").strip()
    data_contratacao = request.form.get("data_contratacao", "").strip()

    parcela = converter_valor_brasileiro(request.form.get("parcela"))
    saldo = converter_valor_brasileiro(request.form.get("saldo"))

    status_boleto = request.form.get("status_boleto", "AGUARDANDO")
    observacao = request.form.get("observacao", "").strip()

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cliente_id
        FROM clientes_compra_dividas
        WHERE id = ?
    """, (id,))
    divida = cursor.fetchone()

    if not divida:
        conn.close()
        return redirect("/compra-divida/clientes")

    cliente_id = divida["cliente_id"]

    cursor.execute("""
        UPDATE clientes_compra_dividas
        SET banco = ?,
            contrato = ?,
            data_contratacao = ?,
            parcela = ?,
            saldo = ?,
            status_boleto = ?,
            observacao = ?
        WHERE id = ?
    """, (
        banco,
        contrato,
        data_contratacao,
        parcela,
        saldo,
        status_boleto,
        observacao,
        id
    ))

    conn.commit()
    conn.close()

    return redirect(f"/compra-divida/cliente/{cliente_id}?aba=dividas")


@app.route("/compra-divida/divida/excluir/<int:id>")
def excluir_divida_compra(id):

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT cliente_id
        FROM clientes_compra_dividas
        WHERE id = ?
    """, (id,))
    divida = cursor.fetchone()

    if not divida:
        conn.close()
        return redirect("/compra-divida/clientes")

    cliente_id = divida["cliente_id"]

    cursor.execute("""
        DELETE FROM clientes_compra_dividas
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(f"/compra-divida/cliente/{cliente_id}?aba=dividas")

@app.route("/admin/clonar-metas", methods=["POST"])
@apenas_master
def clonar_metas():

    competencia_origem = request.form.get("competencia_origem", "").strip()
    competencia_destino = request.form.get("competencia_destino", "").strip()

    if not competencia_origem or not competencia_destino:
        return redirect("/admin?aba=metas")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT usuario_id, produto, meta
        FROM meta_usuario_produto
        WHERE competencia = ?
    """, (competencia_origem,))

    metas_origem = cursor.fetchall()

    for m in metas_origem:
        cursor.execute("""
            SELECT id
            FROM meta_usuario_produto
            WHERE usuario_id = ?
            AND produto = ?
            AND competencia = ?
        """, (m["usuario_id"], m["produto"], competencia_destino))

        existente = cursor.fetchone()

        if existente:
            cursor.execute("""
                UPDATE meta_usuario_produto
                SET meta = ?
                WHERE id = ?
            """, (m["meta"], existente["id"]))
        else:
            cursor.execute("""
                INSERT INTO meta_usuario_produto
                (usuario_id, produto, meta, competencia)
                VALUES (?, ?, ?, ?)
            """, (
                m["usuario_id"],
                m["produto"],
                m["meta"],
                competencia_destino
            ))

    conn.commit()
    conn.close()

    return redirect(f"/admin?aba=metas&competencia={competencia_destino}")


@app.route("/ver-vendas")
def ver_vendas():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM vendas
        ORDER BY id DESC
        LIMIT 20
    """)

    vendas = cursor.fetchall()

    

    conn.close()


   

    return str([dict(v) for v in vendas])
garantir_coluna_competencia_metas()
criar_tabelas_compra_divida()
def atualizar_tabela_usuarios():
    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(usuarios)")
    colunas = [coluna[1] for coluna in cursor.fetchall()]

    if "cpf" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN cpf TEXT")

    if "email" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN email TEXT")

    if "ativo" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN ativo INTEGER DEFAULT 1")

    if "ultimo_login" not in colunas:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN ultimo_login TEXT")

    conn.commit()
    conn.close()
if __name__ == "__main__":
    print("🔥 FLASK INICIANDO...")
    atualizar_tabela_usuarios()
    atualizar_tabela_comissoes()
    atualizar_tabela_clientes_compra()
    atualizar_tabela_avisos()
    criar_tabela_recuperacao_senha()
    app.run(debug=True, host="192.168.0.200", port=5000)