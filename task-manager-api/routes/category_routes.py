from flask import Blueprint, jsonify, request

from controllers import category_controller

category_bp = Blueprint("categories", __name__)


@category_bp.route("/categories", methods=["GET"])
def get_categories():
    return jsonify(category_controller.list_all()), 200


@category_bp.route("/categories", methods=["POST"])
def create_category():
    category = category_controller.create(request.get_json(silent=True))
    return jsonify(category.to_dict()), 201


@category_bp.route("/categories/<int:cat_id>", methods=["PUT"])
def update_category(cat_id):
    category = category_controller.update(cat_id, request.get_json(silent=True))
    return jsonify(category.to_dict()), 200


@category_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
def delete_category(cat_id):
    category_controller.delete(cat_id)
    return jsonify({"message": "Categoria deletada"}), 200
