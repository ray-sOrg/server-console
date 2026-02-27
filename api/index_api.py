from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required
import os

index_api_pb = Blueprint('index_api', __name__)


@index_api_pb.route('/logger')
def logger():
    current_app.logger.debug("FLASK_ENV: %s", os.environ.get('FLASK_ENV'))
    return "Hello, Logger!"


@index_api_pb.route('/index')
@jwt_required()
def index():
    response = {
        "code": 200,
        "message": "Success",
        "data": "index test"
    }
    return jsonify(response)

