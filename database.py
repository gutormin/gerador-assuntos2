"""
database.py
Inicialização do banco de dados SQLite e criação das tabelas.
Cria também o usuário administrador padrão na primeira execução.
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), "assuntos.db")


def get_connection():
    """Abre conexão com o banco, retornando linhas como dicionários."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Cria as tabelas se ainda não existirem e popula dados iniciais."""
    conn = get_connection()
    cur = conn.cursor()

    # --- Usuários ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuario (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            email         TEXT NOT NULL UNIQUE,
            senha_hash    TEXT NOT NULL,
            papel         TEXT NOT NULL CHECK (papel IN
                          ('ADMIN_AUDITOR','EDITOR_REVISOR','SERVIDOR')),
            tentativas    INTEGER NOT NULL DEFAULT 0,
            bloqueado     INTEGER NOT NULL DEFAULT 0,
            criado_em     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    """)

    # --- Tipos de documento (Ofício, E-mail...) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tipo_documento (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nome  TEXT NOT NULL UNIQUE
        )
    """)

    # --- Subtítulos (Requerimento, Compensação...) ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS subtitulo (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nome  TEXT NOT NULL UNIQUE
        )
    """)

    # --- Tags / palavras-chave ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tag (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nome  TEXT NOT NULL UNIQUE
        )
    """)

    # --- Assuntos ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assunto (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo           TEXT NOT NULL,
            subtitulo_id     INTEGER,
            tipo_documento_id INTEGER,
            corpo_modelo     TEXT,
            contador_uso     INTEGER NOT NULL DEFAULT 0,
            criado_por       INTEGER,
            criado_em        TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            atualizado_por   INTEGER,
            atualizado_em    TEXT,
            FOREIGN KEY (subtitulo_id)      REFERENCES subtitulo(id),
            FOREIGN KEY (tipo_documento_id) REFERENCES tipo_documento(id),
            FOREIGN KEY (criado_por)        REFERENCES usuario(id),
            FOREIGN KEY (atualizado_por)    REFERENCES usuario(id)
        )
    """)

    # --- Relação N:N assunto <-> tag ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS assunto_tag (
            assunto_id INTEGER NOT NULL,
            tag_id     INTEGER NOT NULL,
            PRIMARY KEY (assunto_id, tag_id),
            FOREIGN KEY (assunto_id) REFERENCES assunto(id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id)     REFERENCES tag(id)     ON DELETE CASCADE
        )
    """)

    # --- Log de auditoria ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS log_auditoria (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id  INTEGER,
            acao        TEXT NOT NULL,
            entidade    TEXT NOT NULL,
            registro_id INTEGER,
            detalhe     TEXT,
            data_hora   TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (usuario_id) REFERENCES usuario(id)
        )
    """)

    # --- Histórico de versões dos assuntos ---
    cur.execute("""
        CREATE TABLE IF NOT EXISTS historico (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            assunto_id       INTEGER NOT NULL,
            versao           INTEGER NOT NULL,
            dados_anteriores TEXT,
            alterado_por     INTEGER,
            data             TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            FOREIGN KEY (assunto_id)   REFERENCES assunto(id),
            FOREIGN KEY (alterado_por) REFERENCES usuario(id)
        )
    """)

    # --- Dados iniciais ---
    # Usuário admin padrão (troque a senha após o primeiro acesso!)
    cur.execute("SELECT COUNT(*) AS n FROM usuario")
    if cur.fetchone()["n"] == 0:
        cur.execute(
            "INSERT INTO usuario (nome, email, senha_hash, papel) VALUES (?,?,?,?)",
            ("Administrador", "admin@local",
             generate_password_hash("admin123"), "ADMIN_AUDITOR")
        )

    # Tipos de documento iniciais
    for nome in ("Ofício", "E-mail"):
        cur.execute("INSERT OR IGNORE INTO tipo_documento (nome) VALUES (?)", (nome,))

    # Subtítulos iniciais
    for nome in ("Requerimento", "Compensação", "Remarcação",
                 "Designação", "Autorização"):
        cur.execute("INSERT OR IGNORE INTO subtitulo (nome) VALUES (?)", (nome,))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Banco de dados inicializado com sucesso em:", DB_PATH)
