from middlewares.error_handler import NotFoundError, ValidationError
from models.base import get_connection

STATUS_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]

FAIXAS_DESCONTO = ((10000, 0.1), (5000, 0.05), (1000, 0.02))


def _agrupar_pedidos(rows):
    pedidos = {}
    ordem = []
    for row in rows:
        pedido_id = row["id"]
        if pedido_id not in pedidos:
            pedidos[pedido_id] = {
                "id": row["id"],
                "usuario_id": row["usuario_id"],
                "status": row["status"],
                "total": row["total"],
                "criado_em": row["criado_em"],
                "itens": [],
            }
            ordem.append(pedido_id)
        if row["produto_id"] is not None:
            pedidos[pedido_id]["itens"].append(
                {
                    "produto_id": row["produto_id"],
                    "produto_nome": row["produto_nome"] or "Desconhecido",
                    "quantidade": row["quantidade"],
                    "preco_unitario": row["preco_unitario"],
                }
            )
    return [pedidos[pedido_id] for pedido_id in ordem]


_SELECT_PEDIDOS_COM_ITENS = """
    SELECT p.id, p.usuario_id, p.status, p.total, p.criado_em,
           i.produto_id, i.quantidade, i.preco_unitario, pr.nome AS produto_nome
    FROM pedidos p
    LEFT JOIN itens_pedido i ON i.pedido_id = p.id
    LEFT JOIN produtos pr ON pr.id = i.produto_id
    {filtro}
    ORDER BY p.id, i.id
"""


def listar_todos():
    conn = get_connection()
    rows = conn.execute(_SELECT_PEDIDOS_COM_ITENS.format(filtro="")).fetchall()
    return _agrupar_pedidos(rows)


def listar_por_usuario(usuario_id):
    conn = get_connection()
    rows = conn.execute(
        _SELECT_PEDIDOS_COM_ITENS.format(filtro="WHERE p.usuario_id = ?"),
        (usuario_id,),
    ).fetchall()
    return _agrupar_pedidos(rows)


def criar(usuario_id, itens):
    conn = get_connection()
    with conn:
        total = 0
        produtos_reservados = []
        for item in itens:
            produto = conn.execute(
                "SELECT id, nome, preco, estoque FROM produtos WHERE id = ?",
                (item["produto_id"],),
            ).fetchone()
            if produto is None:
                raise NotFoundError(f"Produto {item['produto_id']} não encontrado")
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError(f"Estoque insuficiente para {produto['nome']}")
            total += produto["preco"] * item["quantidade"]
            produtos_reservados.append((produto, item["quantidade"]))

        pedido_id = conn.execute(
            "INSERT INTO pedidos (usuario_id, status, total) VALUES (?, ?, ?)",
            (usuario_id, "pendente", total),
        ).lastrowid

        for produto, quantidade in produtos_reservados:
            conn.execute(
                "INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unitario) "
                "VALUES (?, ?, ?, ?)",
                (pedido_id, produto["id"], quantidade, produto["preco"]),
            )
            conn.execute(
                "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
                (quantidade, produto["id"]),
            )

    return {"pedido_id": pedido_id, "total": total}


def atualizar_status(pedido_id, novo_status):
    conn = get_connection()
    with conn:
        conn.execute(
            "UPDATE pedidos SET status = ? WHERE id = ?", (novo_status, pedido_id)
        )


def calcular_desconto(faturamento):
    for limite, percentual in FAIXAS_DESCONTO:
        if faturamento > limite:
            return faturamento * percentual
    return 0


def relatorio_vendas():
    conn = get_connection()

    total_pedidos = conn.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    faturamento = conn.execute("SELECT SUM(total) FROM pedidos").fetchone()[0] or 0

    contagem_por_status = dict(
        conn.execute(
            "SELECT status, COUNT(*) FROM pedidos GROUP BY status"
        ).fetchall()
    )

    desconto = calcular_desconto(faturamento)

    return {
        "total_pedidos": total_pedidos,
        "faturamento_bruto": round(faturamento, 2),
        "desconto_aplicavel": round(desconto, 2),
        "faturamento_liquido": round(faturamento - desconto, 2),
        "pedidos_pendentes": contagem_por_status.get("pendente", 0),
        "pedidos_aprovados": contagem_por_status.get("aprovado", 0),
        "pedidos_cancelados": contagem_por_status.get("cancelado", 0),
        "ticket_medio": round(faturamento / total_pedidos, 2) if total_pedidos > 0 else 0,
    }
