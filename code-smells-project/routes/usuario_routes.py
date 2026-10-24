from flask import Blueprint, jsonify, request

import controllers.usuario_controller as usuario_controller

usuario_bp = Blueprint("usuarios", __name__)


@usuario_bp.get("/usuarios")
def listar_usuarios():
    usuarios = usuario_controller.listar()
    return jsonify({"dados": usuarios, "sucesso": True}), 200


@usuario_bp.get("/usuarios/<int:usuario_id>")
def buscar_usuario(usuario_id):
    usuario = usuario_controller.buscar_por_id(usuario_id)
    return jsonify({"dados": usuario, "sucesso": True}), 200


@usuario_bp.post("/usuarios")
def criar_usuario():
    usuario_id = usuario_controller.criar(request.get_json())
    return jsonify({"dados": {"id": usuario_id}, "sucesso": True}), 201


@usuario_bp.post("/login")
def login():
    usuario = usuario_controller.login(request.get_json())
    return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200
