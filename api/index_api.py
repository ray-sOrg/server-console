from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app import app
import os

index_api_pb = Blueprint('index_api', __name__)


@index_api_pb.route('/logger')
def logger():
    app.logger.debug("FLASK_ENV: %s", os.environ.get('FLASK_ENV'))
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

