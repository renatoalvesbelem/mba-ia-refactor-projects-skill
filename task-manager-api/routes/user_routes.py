from flask import Blueprint, jsonify, request

from controllers import user_controller
from middlewares.auth import require_admin

user_bp = Blueprint("users", __name__)


@user_bp.route("/users", methods=["GET"])
def get_users():
    return jsonify(user_controller.list_all()), 200


@user_bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    return jsonify(user_controller.get(user_id)), 200


@user_bp.route("/users", methods=["POST"])
def create_user():
    user = user_controller.create(request.get_json(silent=True))
    return jsonify(user.to_dict()), 201


@user_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    user = user_controller.update(user_id, request.get_json(silent=True))
    return jsonify(user.to_dict()), 200


@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
@require_admin
def delete_user(user_id):
    user_controller.delete(user_id)
    return jsonify({"message": "Usuário deletado com sucesso"}), 200


@user_bp.route("/users/<int:user_id>/tasks", methods=["GET"])
def get_user_tasks(user_id):
    return jsonify(user_controller.list_tasks(user_id)), 200


@user_bp.route("/login", methods=["POST"])
def login():
    user = user_controller.login(request.get_json(silent=True))
    return (
        jsonify(
            {
                "message": "Login realizado com sucesso",
                "user": user.to_dict(),
                "token": "fake-jwt-token-" + str(user.id),
            }
        ),
        200,
    )
