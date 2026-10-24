from flask import Blueprint, jsonify, request

from controllers import task_controller

task_bp = Blueprint("tasks", __name__)


@task_bp.route("/tasks", methods=["GET"])
def get_tasks():
    return jsonify(task_controller.list_all()), 200


@task_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    return jsonify(task_controller.get(task_id)), 200


@task_bp.route("/tasks", methods=["POST"])
def create_task():
    task = task_controller.create(request.get_json(silent=True))
    return jsonify(task.to_dict()), 201


@task_bp.route("/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    task = task_controller.update(task_id, request.get_json(silent=True))
    return jsonify(task.to_dict()), 200


@task_bp.route("/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    task_controller.delete(task_id)
    return jsonify({"message": "Task deletada com sucesso"}), 200


@task_bp.route("/tasks/search", methods=["GET"])
def search_tasks():
    result = task_controller.search(
        request.args.get("q", ""),
        request.args.get("status", ""),
        request.args.get("priority", ""),
        request.args.get("user_id", ""),
    )
    return jsonify(result), 200


@task_bp.route("/tasks/stats", methods=["GET"])
def task_stats():
    return jsonify(task_controller.stats()), 200
