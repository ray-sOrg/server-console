from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required
import os

test_api_pb = Blueprint('test_api', __name__)


@test_api_pb.route('/test/flask_env', methods=["GET"])
@jwt_required()
def test_flask_env():
    FLASK_ENV = os.environ.get('FLASK_ENV')
    response = {
        "code": 200,
        "message": "Success",
        "data": FLASK_ENV
    }
    return jsonify(response)


def test_celery_task():
    return 'task completed'


@test_api_pb.route('/test/celery', methods=["GET"])
@jwt_required()
def trigger_celery_task():
    task = current_app.celery.send_task("test_celery_task")
    response = {
        "code": 200,
        "message": "Celery task has been triggered",
        "task_id": task.id
    }
    return jsonify(response)