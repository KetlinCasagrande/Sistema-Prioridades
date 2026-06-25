from flask import Flask, flash, render_template, request, redirect, session, g
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
from datetime import datetime, timedelta
from flask import send_file



app = Flask(__name__)
app.secret_key = "123"

def db():
    conn = sqlite3.connect("banco.db")
    conn.row_factory = sqlite3.Row
    return conn


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

        usuario = request.form["usuario"]
        senha = request.form["senha"]

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM usuarios
            WHERE usuario = ?
        """, (usuario,))

        user = cursor.fetchone()

        conn.close()

        # LOGIN CORRETO
        if user and bcrypt.checkpw(
            senha.encode(),
            user["senha"].encode()
        ):

            session["usuario"] = user["usuario"]
            session["tipo"] = user["tipo"]
            session["usuario_id"] = user["id"]

            return redirect("/home")

        else:
            erro = "Login inválido"

    return render_template(
        "login.html",
        erro=erro
    )
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
@app.route("/home")
def home():

    if not verificar_login():
        return redirect("/")

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
            elif produto == "CLT":
                status = "LIBERADA" if comissao >= 3.5 else "PRECISA_LIBERACAO"
            elif produto == "INSS":
                status = "LIBERADA" if comissao >= 7 else "PRECISA_LIBERACAO"
            elif produto == "FGTS":
                status = "LIBERADA" if comissao >= 10 else "PRECISA_LIBERACAO"
            elif produto == "COMPRA_DIVIDA":
                status = "LIBERADA" if comissao >= 9 else "PRECISA_LIBERACAO"
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
        bancos=bancos,
        titulo="CLT",
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

    cursor.execute("""
        SELECT
            meta_usuario_produto.*,
            usuarios.usuario
        FROM meta_usuario_produto
        JOIN usuarios
            ON usuarios.id = meta_usuario_produto.usuario_id
        ORDER BY usuarios.usuario
    """)
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
def salvar_meta_vendedora():

    conn = conectar()
    cursor = conn.cursor()

    id_meta = request.form["id"]
    meta = request.form["meta"]

    cursor.execute("""
        UPDATE meta_usuario_produto
        SET meta = ?
        WHERE id = ?
    """, (meta, id_meta))

    conn.commit()
    conn.close()

    return redirect("/admin")


# =========================
# USUÁRIOS
# =========================
@app.route("/admin/usuario/criar", methods=["POST"])
@apenas_admin
def criar_usuario():

    try:
        usuario = request.form["usuario"]
        senha = request.form["senha"]
        tipo = request.form["tipo"]

        senha_hash = bcrypt.hashpw(
            senha.encode(),
            bcrypt.gensalt()
        ).decode()

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO usuarios
            (usuario, senha, tipo)
            VALUES (?, ?, ?)
        """, (
            usuario,
            senha_hash,
            tipo
        ))

        conn.commit()
        
        conn.close()

        print("✔ USUÁRIO CRIADO:", usuario)

        return redirect("/admin")

    except Exception as e:
        print("❌ ERRO AO CRIAR USUÁRIO:", e)
        return redirect("/admin")


@app.route("/admin/usuario/editar/<int:id>", methods=["POST"])
@apenas_admin
def editar_usuario(id):

    usuario = request.form["usuario"]
    tipo = request.form["tipo"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET usuario = ?, tipo = ?
        WHERE id = ?
    """, (
        usuario,
        tipo,
        id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


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

    return redirect("/admin")


# =========================
# AVISOS
# =========================
@app.route("/admin/aviso/criar", methods=["POST"])
@apenas_admin
def criar_aviso():

    titulo = request.form["titulo"]
    mensagem = request.form["mensagem"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO avisos
        (titulo, mensagem)
        VALUES (?, ?)
    """, (
        titulo,
        mensagem
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")


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

    titulo = request.form["titulo"]
    mensagem = request.form["mensagem"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE avisos
        SET titulo = ?, mensagem = ?
        WHERE id = ?
    """, (
        titulo,
        mensagem,
        id
    ))

    conn.commit()
    conn.close()

    return redirect("/admin")

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

            parcela_txt = parcelas[i].replace("R$", "").replace(".", "").replace(",", ".").strip()
            saldo_txt = saldos[i].replace("R$", "").replace(".", "").replace(",", ".").strip()

            try:
                parcela_float = float(parcela_txt)
            except:
                parcela_float = 0.0

            try:
                saldo_float = float(saldo_txt)
            except:
                saldo_float = 0.0

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
    return render_template(
        "termos.html",
        texto_termo=None,
        tipo=session.get("tipo")
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
        DELETE FROM meta_usuario_produto
        WHERE id = ?
    """, (id,))

    conn.commit()
    conn.close()

    return redirect(request.referrer or "/admin")


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

    for nome_aba, df in abas.items():

        produto_aba = nome_aba.strip().upper()

        # normaliza colunas
        df.columns = [c.strip().lower() for c in df.columns]

        for _, row in df.iterrows():

            banco = str(row.get("banco", "")).strip().upper()
            tabela_nome = str(row.get("tabela", "")).strip().upper()
            prazo = str(row.get("prazo", "")).strip().upper()
            promotora = str(row.get("promotora", "")).strip().upper()
            comissao = str(row.get("comissão", row.get("comissao", "0")))

            # normalização forte
            comissao = comissao.replace(",", ".").strip()

            if not banco or not tabela_nome:
                continue

            cursor.execute("""
                SELECT id FROM comissoes
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
                    SET comissao = ?
                    WHERE id = ?
                """, (comissao, existe["id"]))

                total_atualizados += 1

            else:
                cursor.execute("""
                    INSERT INTO comissoes
                    (banco, produto, tabela_nome, comissao, prazo, promotora, ativo)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                """, (
                    banco,
                    produto_aba,
                    tabela_nome,
                    comissao,
                    prazo,
                    promotora
                ))

                total_novos += 1

    conn.commit()
    conn.close()

    return f"✔ Importação concluída! Novos: {total_novos} | Atualizados: {total_atualizados}"

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

    historico = cursor.fetchall()

    conn.close()

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

    conn = sqlite3.connect("banco.db")
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE acessos_banco
        SET descricao = ?,
            login = ?,
            senha = ?
        WHERE id = ?
    """, (

        request.form["descricao"],
        request.form["login"],
        request.form["senha"],
        id

    ))

    conn.commit()
    conn.close()

    return redirect("/bancos")


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
def adicionar_meta():

    conn = conectar()
    cursor = conn.cursor()

    usuario_id = request.form["usuario_id"]
    produto = request.form["produto"]
    meta = request.form["meta"]

    cursor.execute("""
        INSERT INTO meta_usuario_produto
        (usuario_id, produto, meta)
        VALUES (?, ?, ?)
    """, (usuario_id, produto, meta))

    conn.commit()
    conn.close()

    return redirect("/admin")
# =========================
# MINHAS VENDAS
# =========================
@app.route("/vendas")
def minhas_vendas():

    if not verificar_login():
        return redirect("/")

    conn = conectar()
    cursor = conn.cursor()

    # =========================
    # METAS DA VENDEDORA
    # =========================
    cursor.execute("""
        SELECT *
        FROM meta_usuario_produto
        WHERE usuario_id = CAST(? AS INTEGER)
    """, (session["usuario_id"],))

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
        AND strftime('%Y-%m', data) = strftime('%Y-%m', 'now')
        GROUP BY UPPER(produto)
    """, (session["usuario_id"],))

    vendas_mes = cursor.fetchall()

    vendas_dict = {
        v["produto"]: float(v["total"] or 0)
        for v in vendas_mes
    }

    # =========================
    # HISTÓRICO
    # =========================
    cursor.execute("""
        SELECT *
        FROM vendas
        WHERE usuario_id = ?
        ORDER BY id DESC
    """, (session["usuario_id"],))

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

        progresso_produtos.append({
            "produto": produto,
            "meta": meta,
            "vendido": vendido,
            "percentual": percentual,
            "falta": meta - vendido
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

        tipo=session["tipo"],
        usuario=session["usuario"]
    )

@app.route("/admin/comissoes/limpar-promotora", methods=["POST"])
@apenas_master
def limpar_comissoes_promotora():

    promotora = request.form.get("promotora", "").strip()

    if not promotora:
        return redirect("/admin?aba=comissoes")

    removidas = limpar_promotora(promotora)

    registrar_auditoria(
        "LIMPAR_PROMOTORA",
        f"Promotora: {promotora} | Registros removidos: {removidas}"
    )

    return redirect("/admin?aba=comissoes")

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
if __name__ == "__main__":
    print("🔥 FLASK INICIANDO...")
    app.run(host="192.168.0.63", port=5000, debug=True)