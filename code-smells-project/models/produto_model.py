from models.base import get_connection

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]


def _to_dict(row):
    return {
        "id": row["id"],
        "nome": row["nome"],
        "descricao": row["descricao"],
        "preco": row["preco"],
        "estoque": row["estoque"],
        "categoria": row["categoria"],
        "ativo": row["ativo"],
        "criado_em": row["criado_em"],
    }


def listar_todos():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM produtos").fetchall()
    return [_to_dict(row) for row in rows]


def buscar_por_id(produto_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    return _to_dict(row) if row else None


def criar(nome, descricao, preco, estoque, categoria):
    conn = get_connection()
    with conn:
        cursor = conn.execute(
            "INSERT INTO produtos (nome, descricao, preco, estoque, categoria) VALUES (?, ?, ?, ?, ?)",
            (nome, descricao, preco, estoque, categoria),
        )
    return cursor.lastrowid


def atualizar(produto_id, nome, descricao, preco, estoque, categoria):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE produtos SET nome = ?, descricao = ?, preco = ?, estoque = ?, categoria = ? WHERE id = ?",
            (nome, descricao, preco, estoque, categoria, produto_id),
        )


def deletar(produto_id):
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))


def buscar(termo=None, categoria=None, preco_min=None, preco_max=None):
    conn = get_connection()
    clauses = []
    params = []

    if termo:
        clauses.append("(nome LIKE ? OR descricao LIKE ?)")
        params += [f"%{termo}%", f"%{termo}%"]
    if categoria:
        clauses.append("categoria = ?")
        params.append(categoria)
    if preco_min is not None:
        clauses.append("preco >= ?")
        params.append(preco_min)
    if preco_max is not None:
        clauses.append("preco <= ?")
        params.append(preco_max)

    sql = "SELECT * FROM produtos"
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)

    rows = conn.execute(sql, params).fetchall()
    return [_to_dict(row) for row in rows]
