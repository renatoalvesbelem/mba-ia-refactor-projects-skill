from flask import Blueprint, jsonify, request

import controllers.pedido_controller as pedido_controller

pedido_bp = Blueprint("pedidos", __name__)


@pedido_bp.post("/pedidos")
def criar_pedido():
    resultado = pedido_controller.criar(request.get_json())
    return (
        jsonify({"dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso"}),
        201,
    )


@pedido_bp.get("/pedidos")
def listar_todos_pedidos():
    pedidos = pedido_controller.listar_todos()
    return jsonify({"dados": pedidos, "sucesso": True}), 200


@pedido_bp.get("/pedidos/usuario/<int:usuario_id>")
def listar_pedidos_usuario(usuario_id):
    pedidos = pedido_controller.listar_por_usuario(usuario_id)
    return jsonify({"dados": pedidos, "sucesso": True}), 200


@pedido_bp.put("/pedidos/<int:pedido_id>/status")
def atualizar_status_pedido(pedido_id):
    pedido_controller.atualizar_status(pedido_id, request.get_json())
    return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200
