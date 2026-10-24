from flask import Blueprint, jsonify, request

import controllers.pedido_controller as pedido_controller
import controllers.sistema_controller as sistema_controller
from middlewares.auth import require_admin

sistema_bp = Blueprint("sistema", __name__)


@sistema_bp.get("/")
def index():
    return jsonify(
        {
            "mensagem": "Bem-vindo à API da Loja",
            "versao": "1.0.0",
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        }
    )


@sistema_bp.get("/relatorios/vendas")
def relatorio_vendas():
    relatorio = pedido_controller.relatorio_vendas()
    return jsonify({"dados": relatorio, "sucesso": True}), 200


@sistema_bp.get("/health")
def health_check():
    return jsonify(sistema_controller.health_check()), 200


@sistema_bp.post("/admin/reset-db")
@require_admin
def reset_database():
    sistema_controller.resetar_banco()
    return jsonify({"mensagem": "Banco de dados resetado", "sucesso": True}), 200


@sistema_bp.post("/admin/query")
@require_admin
def executar_query():
    resultado = sistema_controller.executar_query(request.get_json())
    return jsonify({"dados": resultado, "sucesso": True}), 200
