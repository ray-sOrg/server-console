from flask import Blueprint, jsonify
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