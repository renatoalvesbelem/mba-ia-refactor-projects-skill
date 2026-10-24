from werkzeug.security import check_password_hash, generate_password_hash

from models.base import get_connection

PUBLIC_FIELDS = ("id", "nome", "email", "tipo", "criado_em")
AUTH_FIELDS = ("id", "nome", "email", "tipo")


def _to_public_dict(row):
    return {campo: row[campo] for campo in PUBLIC_FIELDS}


def _to_auth_dict(row):
    return {campo: row[campo] for campo in AUTH_FIELDS}


def listar_todos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM usuarios").fetchall()
    return [_to_public_dict(row) for row in rows]


def buscar_por_id(usuario_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    return _to_public_dict(row) if row else None


def buscar_por_email(email):
    conn = get_connection()
    return conn.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()


def criar(nome, email, senha, tipo="cliente"):
    conn = get_connection()
    senha_hash = generate_password_hash(senha)
    with conn:
        cursor = conn.execute(
            "INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
            (nome, email, senha_hash, tipo),
        )
    return cursor.lastrowid


def autenticar(email, senha):
    row = buscar_por_email(email)
    if row and check_password_hash(row["senha"], senha):
        return _to_auth_dict(row)
    return None
