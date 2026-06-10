"""
app.py
Aplicação principal do Sistema Gerador de Assuntos para Ofícios e E-mails.

Tecnologias: Python + Flask + SQLite.
Perfis: ADMIN_AUDITOR, EDITOR_REVISOR, SERVIDOR.

Execute com:  python app.py
Acesse em:    http://127.0.0.1:5000
"""
import json
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify)
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_connection, init_db

app = Flask(__name__)
# Em produção, troque por uma chave secreta forte e mantenha-a fora do código.
app.secret_key = "troque-esta-chave-secreta-em-producao"

MAX_TENTATIVAS = 5  # bloqueio após este número de logins falhos


# ----------------------------------------------------------------------------
# Funções auxiliares de segurança / auditoria
# ----------------------------------------------------------------------------
def registrar_log(usuario_id, acao, entidade, registro_id=None, detalhe=None):
    """Grava uma entrada na trilha de auditoria."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO log_auditoria
           (usuario_id, acao, entidade, registro_id, detalhe)
           VALUES (?,?,?,?,?)""",
        (usuario_id, acao, entidade, registro_id, detalhe)
    )
    conn.commit()
    conn.close()


def login_obrigatorio(f):
    """Garante que há um usuário logado."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def papel_obrigatorio(*papeis):
    """Restringe a rota a determinados papéis."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "usuario_id" not in session:
                return redirect(url_for("login"))
            if session.get("papel") not in papeis:
                flash("Você não tem permissão para acessar esta área.", "erro")
                return redirect(url_for("consulta"))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ----------------------------------------------------------------------------
# Autenticação
# ----------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    if "usuario_id" in session:
        return redirect(url_for("consulta"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM usuario WHERE email = ?", (email,)
        ).fetchone()

        if user is None:
            conn.close()
            flash("E-mail ou senha inválidos.", "erro")
            return render_template("login.html")

        if user["bloqueado"]:
            conn.close()
            flash("Usuário bloqueado por excesso de tentativas. "
                  "Procure o administrador.", "erro")
            return render_template("login.html")

        if check_password_hash(user["senha_hash"], senha):
            # Sucesso: zera tentativas e cria sessão
            conn.execute("UPDATE usuario SET tentativas = 0 WHERE id = ?",
                         (user["id"],))
            conn.commit()
            conn.close()
            session.clear()
            session["usuario_id"] = user["id"]
            session["nome"] = user["nome"]
            session["papel"] = user["papel"]
            session.permanent = True
            registrar_log(user["id"], "LOGIN", "usuario", user["id"])
            return redirect(url_for("consulta"))
        else:
            # Falha: incrementa tentativas e bloqueia se passar do limite
            tentativas = user["tentativas"] + 1
            bloqueado = 1 if tentativas >= MAX_TENTATIVAS else 0
            conn.execute(
                "UPDATE usuario SET tentativas = ?, bloqueado = ? WHERE id = ?",
                (tentativas, bloqueado, user["id"])
            )
            conn.commit()
            conn.close()
            if bloqueado:
                flash("Usuário bloqueado por excesso de tentativas.", "erro")
            else:
                restantes = MAX_TENTATIVAS - tentativas
                flash(f"E-mail ou senha inválidos. "
                      f"Tentativas restantes: {restantes}.", "erro")
            return render_template("login.html")

    return render_template("login.html")


@app.route("/logout")
@login_obrigatorio
def logout():
    registrar_log(session["usuario_id"], "LOGOUT", "usuario",
                  session["usuario_id"])
    session.clear()
    flash("Sessão encerrada.", "ok")
    return redirect(url_for("login"))


# ----------------------------------------------------------------------------
# Consulta de assuntos (todos os perfis)
# ----------------------------------------------------------------------------
@app.route("/consulta")
@login_obrigatorio
def consulta():
    termo = request.args.get("q", "").strip()
    tipo_id = request.args.get("tipo", "").strip()
    subtitulo_id = request.args.get("subtitulo", "").strip()
    ordem = request.args.get("ordem", "recentes")

    conn = get_connection()

    sql = """
        SELECT a.*, t.nome AS tipo_nome, s.nome AS subtitulo_nome
        FROM assunto a
        LEFT JOIN tipo_documento t ON a.tipo_documento_id = t.id
        LEFT JOIN subtitulo s      ON a.subtitulo_id = s.id
        WHERE 1=1
    """
    params = []

    if termo:
        # busca no título, corpo e nas tags
        sql += """ AND (
            a.titulo LIKE ? OR a.corpo_modelo LIKE ? OR
            a.id IN (
                SELECT at.assunto_id FROM assunto_tag at
                JOIN tag tg ON tg.id = at.tag_id
                WHERE tg.nome LIKE ?
            )
        )"""
        like = f"%{termo}%"
        params += [like, like, like]

    if tipo_id:
        sql += " AND a.tipo_documento_id = ?"
        params.append(tipo_id)

    if subtitulo_id:
        sql += " AND a.subtitulo_id = ?"
        params.append(subtitulo_id)

    if ordem == "mais_usados":
        sql += " ORDER BY a.contador_uso DESC, a.id DESC"
    elif ordem == "alfabetica":
        sql += " ORDER BY a.titulo COLLATE NOCASE ASC"
    else:  # recentes
        sql += " ORDER BY a.id DESC"

    assuntos = conn.execute(sql, params).fetchall()

    # carrega tags de cada assunto
    resultados = []
    for a in assuntos:
        tags = conn.execute(
            """SELECT tg.nome FROM tag tg
               JOIN assunto_tag at ON at.tag_id = tg.id
               WHERE at.assunto_id = ?""", (a["id"],)
        ).fetchall()
        item = dict(a)
        item["tags"] = [t["nome"] for t in tags]
        resultados.append(item)

    tipos = conn.execute("SELECT * FROM tipo_documento ORDER BY nome").fetchall()
    subtitulos = conn.execute("SELECT * FROM subtitulo ORDER BY nome").fetchall()
    conn.close()

    return render_template("consulta.html", assuntos=resultados, tipos=tipos,
                           subtitulos=subtitulos, termo=termo,
                           tipo_sel=tipo_id, subtitulo_sel=subtitulo_id,
                           ordem=ordem)


@app.route("/assunto/<int:assunto_id>/copiar", methods=["POST"])
@login_obrigatorio
def copiar_assunto(assunto_id):
    """Incrementa o contador de uso quando o assunto é copiado."""
    conn = get_connection()
    conn.execute("UPDATE assunto SET contador_uso = contador_uso + 1 WHERE id = ?",
                 (assunto_id,))
    conn.commit()
    conn.close()
    registrar_log(session["usuario_id"], "COPIAR", "assunto", assunto_id)
    return jsonify({"ok": True})


# ----------------------------------------------------------------------------
# Cadastro / edição de assuntos (Admin e Editor)
# ----------------------------------------------------------------------------
@app.route("/assunto/novo", methods=["GET", "POST"])
@papel_obrigatorio("ADMIN_AUDITOR", "EDITOR_REVISOR")
def novo_assunto():
    conn = get_connection()
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        subtitulo_id = request.form.get("subtitulo_id") or None
        tipo_id = request.form.get("tipo_documento_id") or None
        corpo = request.form.get("corpo_modelo", "").strip()
        tags_raw = request.form.get("tags", "").strip()

        if not titulo:
            flash("O título é obrigatório.", "erro")
            conn.close()
            return redirect(url_for("novo_assunto"))

        cur = conn.execute(
            """INSERT INTO assunto
               (titulo, subtitulo_id, tipo_documento_id, corpo_modelo, criado_por)
               VALUES (?,?,?,?,?)""",
            (titulo, subtitulo_id, tipo_id, corpo, session["usuario_id"])
        )
        assunto_id = cur.lastrowid
        _salvar_tags(conn, assunto_id, tags_raw)
        conn.commit()
        conn.close()
        registrar_log(session["usuario_id"], "CRIAR", "assunto", assunto_id, titulo)
        flash("Assunto cadastrado com sucesso.", "ok")
        return redirect(url_for("consulta"))

    tipos = conn.execute("SELECT * FROM tipo_documento ORDER BY nome").fetchall()
    subtitulos = conn.execute("SELECT * FROM subtitulo ORDER BY nome").fetchall()
    conn.close()
    return render_template("assunto_form.html", assunto=None, tipos=tipos,
                           subtitulos=subtitulos, tags_texto="")


@app.route("/assunto/<int:assunto_id>/editar", methods=["GET", "POST"])
@papel_obrigatorio("ADMIN_AUDITOR", "EDITOR_REVISOR")
def editar_assunto(assunto_id):
    conn = get_connection()
    assunto = conn.execute("SELECT * FROM assunto WHERE id = ?",
                           (assunto_id,)).fetchone()
    if assunto is None:
        conn.close()
        flash("Assunto não encontrado.", "erro")
        return redirect(url_for("consulta"))

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        subtitulo_id = request.form.get("subtitulo_id") or None
        tipo_id = request.form.get("tipo_documento_id") or None
        corpo = request.form.get("corpo_modelo", "").strip()
        tags_raw = request.form.get("tags", "").strip()

        if not titulo:
            flash("O título é obrigatório.", "erro")
            conn.close()
            return redirect(url_for("editar_assunto", assunto_id=assunto_id))

        # salva versão anterior no histórico
        versao = conn.execute(
            "SELECT COALESCE(MAX(versao),0)+1 AS v FROM historico WHERE assunto_id = ?",
            (assunto_id,)
        ).fetchone()["v"]
        conn.execute(
            """INSERT INTO historico (assunto_id, versao, dados_anteriores, alterado_por)
               VALUES (?,?,?,?)""",
            (assunto_id, versao, json.dumps(dict(assunto), ensure_ascii=False),
             session["usuario_id"])
        )

        conn.execute(
            """UPDATE assunto SET titulo=?, subtitulo_id=?, tipo_documento_id=?,
               corpo_modelo=?, atualizado_por=?, atualizado_em=datetime('now','localtime')
               WHERE id=?""",
            (titulo, subtitulo_id, tipo_id, corpo, session["usuario_id"], assunto_id)
        )
        conn.execute("DELETE FROM assunto_tag WHERE assunto_id = ?", (assunto_id,))
        _salvar_tags(conn, assunto_id, tags_raw)
        conn.commit()
        conn.close()
        registrar_log(session["usuario_id"], "EDITAR", "assunto", assunto_id, titulo)
        flash("Assunto atualizado com sucesso.", "ok")
        return redirect(url_for("consulta"))

    tipos = conn.execute("SELECT * FROM tipo_documento ORDER BY nome").fetchall()
    subtitulos = conn.execute("SELECT * FROM subtitulo ORDER BY nome").fetchall()
    tags = conn.execute(
        """SELECT tg.nome FROM tag tg
           JOIN assunto_tag at ON at.tag_id = tg.id
           WHERE at.assunto_id = ?""", (assunto_id,)
    ).fetchall()
    tags_texto = ", ".join(t["nome"] for t in tags)
    conn.close()
    return render_template("assunto_form.html", assunto=assunto, tipos=tipos,
                           subtitulos=subtitulos, tags_texto=tags_texto)


@app.route("/assunto/<int:assunto_id>/excluir", methods=["POST"])
@papel_obrigatorio("ADMIN_AUDITOR", "EDITOR_REVISOR")
def excluir_assunto(assunto_id):
    conn = get_connection()
    conn.execute("DELETE FROM assunto_tag WHERE assunto_id = ?", (assunto_id,))
    conn.execute("DELETE FROM assunto WHERE id = ?", (assunto_id,))
    conn.commit()
    conn.close()
    registrar_log(session["usuario_id"], "EXCLUIR", "assunto", assunto_id)
    flash("Assunto excluído.", "ok")
    return redirect(url_for("consulta"))


def _salvar_tags(conn, assunto_id, tags_raw):
    """Recebe tags separadas por vírgula, cria as que faltam e vincula ao assunto."""
    nomes = [t.strip() for t in tags_raw.split(",") if t.strip()]
    for nome in nomes:
        conn.execute("INSERT OR IGNORE INTO tag (nome) VALUES (?)", (nome,))
        tag = conn.execute("SELECT id FROM tag WHERE nome = ?", (nome,)).fetchone()
        conn.execute(
            "INSERT OR IGNORE INTO assunto_tag (assunto_id, tag_id) VALUES (?,?)",
            (assunto_id, tag["id"])
        )


# ----------------------------------------------------------------------------
# Listas cadastráveis: tipos de documento e subtítulos (Admin e Editor)
# ----------------------------------------------------------------------------
@app.route("/cadastros", methods=["GET"])
@papel_obrigatorio("ADMIN_AUDITOR", "EDITOR_REVISOR")
def cadastros():
    conn = get_connection()
    tipos = conn.execute("SELECT * FROM tipo_documento ORDER BY nome").fetchall()
    subtitulos = conn.execute("SELECT * FROM subtitulo ORDER BY nome").fetchall()
    tags = conn.execute("SELECT * FROM tag ORDER BY nome").fetchall()
    conn.close()
    return render_template("cadastros.html", tipos=tipos,
                           subtitulos=subtitulos, tags=tags)


@app.route("/cadastros/<entidade>/novo", methods=["POST"])
@papel_obrigatorio("ADMIN_AUDITOR", "EDITOR_REVISOR")
def cadastro_novo(entidade):
    tabela = {"tipo": "tipo_documento", "subtitulo": "subtitulo",
              "tag": "tag"}.get(entidade)
    if not tabela:
        flash("Entidade inválida.", "erro")
        return redirect(url_for("cadastros"))
    nome = request.form.get("nome", "").strip()
    if nome:
        conn = get_connection()
        try:
            conn.execute(f"INSERT INTO {tabela} (nome) VALUES (?)", (nome,))
            conn.commit()
            registrar_log(session["usuario_id"], "CRIAR", tabela, None, nome)
            flash("Item adicionado.", "ok")
        except Exception:
            flash("Esse item já existe.", "erro")
        conn.close()
    return redirect(url_for("cadastros"))


@app.route("/cadastros/<entidade>/<int:item_id>/excluir", methods=["POST"])
@papel_obrigatorio("ADMIN_AUDITOR", "EDITOR_REVISOR")
def cadastro_excluir(entidade, item_id):
    tabela = {"tipo": "tipo_documento", "subtitulo": "subtitulo",
              "tag": "tag"}.get(entidade)
    if not tabela:
        flash("Entidade inválida.", "erro")
        return redirect(url_for("cadastros"))
    conn = get_connection()
    conn.execute(f"DELETE FROM {tabela} WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    registrar_log(session["usuario_id"], "EXCLUIR", tabela, item_id)
    flash("Item removido.", "ok")
    return redirect(url_for("cadastros"))


# ----------------------------------------------------------------------------
# Gestão de usuários (apenas Admin/Auditor)
# ----------------------------------------------------------------------------
@app.route("/usuarios", methods=["GET"])
@papel_obrigatorio("ADMIN_AUDITOR")
def usuarios():
    conn = get_connection()
    lista = conn.execute("SELECT * FROM usuario ORDER BY nome").fetchall()
    conn.close()
    return render_template("usuarios.html", usuarios=lista)


@app.route("/usuarios/novo", methods=["POST"])
@papel_obrigatorio("ADMIN_AUDITOR")
def usuario_novo():
    nome = request.form.get("nome", "").strip()
    email = request.form.get("email", "").strip()
    senha = request.form.get("senha", "")
    papel = request.form.get("papel", "")
    if not (nome and email and senha and papel):
        flash("Preencha todos os campos.", "erro")
        return redirect(url_for("usuarios"))
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO usuario (nome, email, senha_hash, papel) VALUES (?,?,?,?)",
            (nome, email, generate_password_hash(senha), papel)
        )
        conn.commit()
        registrar_log(session["usuario_id"], "CRIAR", "usuario", None, email)
        flash("Usuário criado.", "ok")
    except Exception:
        flash("Já existe um usuário com esse e-mail.", "erro")
    conn.close()
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:user_id>/desbloquear", methods=["POST"])
@papel_obrigatorio("ADMIN_AUDITOR")
def usuario_desbloquear(user_id):
    conn = get_connection()
    conn.execute("UPDATE usuario SET bloqueado=0, tentativas=0 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    registrar_log(session["usuario_id"], "DESBLOQUEAR", "usuario", user_id)
    flash("Usuário desbloqueado.", "ok")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:user_id>/excluir", methods=["POST"])
@papel_obrigatorio("ADMIN_AUDITOR")
def usuario_excluir(user_id):
    if user_id == session["usuario_id"]:
        flash("Você não pode excluir o próprio usuário.", "erro")
        return redirect(url_for("usuarios"))
    conn = get_connection()
    conn.execute("DELETE FROM usuario WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    registrar_log(session["usuario_id"], "EXCLUIR", "usuario", user_id)
    flash("Usuário excluído.", "ok")
    return redirect(url_for("usuarios"))


# ----------------------------------------------------------------------------
# Auditoria: logs e histórico (apenas Admin/Auditor)
# ----------------------------------------------------------------------------
@app.route("/auditoria")
@papel_obrigatorio("ADMIN_AUDITOR")
def auditoria():
    conn = get_connection()
    logs = conn.execute(
        """SELECT l.*, u.nome AS usuario_nome
           FROM log_auditoria l
           LEFT JOIN usuario u ON u.id = l.usuario_id
           ORDER BY l.id DESC LIMIT 300"""
    ).fetchall()
    conn.close()
    return render_template("auditoria.html", logs=logs)


@app.context_processor
def injeta_usuario():
    """Disponibiliza dados do usuário logado em todos os templates."""
    return {
        "usuario_logado": session.get("nome"),
        "papel_logado": session.get("papel"),
    }


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
