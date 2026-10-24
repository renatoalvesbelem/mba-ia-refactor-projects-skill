from models.base import get_connection


def contar(tabela):
    conn = get_connection()
    return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]


def resetar_tudo():
    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM itens_pedido")
        conn.execute("DELETE FROM pedidos")
        conn.execute("DELETE FROM produtos")
        conn.execute("DELETE FROM usuarios")


def executar_select(sql):
    conn = get_connection()
    rows = conn.execute(sql).fetchall()
    return [dict(row) for row in rows]
