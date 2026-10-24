from flask import Blueprint, jsonify, request

import controllers.produto_controller as produto_controller

produto_bp = Blueprint("produtos", __name__)


@produto_bp.get("/produtos")
def listar_produtos():
    produtos = produto_controller.listar()
    return jsonify({"dados": produtos, "sucesso": True}), 200


@produto_bp.get("/produtos/busca")
def buscar_produtos():
    termo = request.args.get("q", "")
    categoria = request.args.get("categoria", None)
    preco_min = request.args.get("preco_min", None)
    preco_max = request.args.get("preco_max", None)

    resultados = produto_controller.buscar(termo, categoria, preco_min, preco_max)
    return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200


@produto_bp.get("/produtos/<int:produto_id>")
def buscar_produto(produto_id):
    produto = produto_controller.buscar_por_id(produto_id)
    return jsonify({"dados": produto, "sucesso": True}), 200


@produto_bp.post("/produtos")
def criar_produto():
    produto_id = produto_controller.criar(request.get_json())
    return (
        jsonify({"dados": {"id": produto_id}, "sucesso": True, "mensagem": "Produto criado"}),
        201,
    )


@produto_bp.put("/produtos/<int:produto_id>")
def atualizar_produto(produto_id):
    produto_controller.atualizar(produto_id, request.get_json())
    return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200


@produto_bp.delete("/produtos/<int:produto_id>")
def deletar_produto(produto_id):
    produto_controller.deletar(produto_id)
    return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200
