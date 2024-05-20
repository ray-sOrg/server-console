from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

index_api_pb = Blueprint('index_api', __name__)


@index_api_pb.route('/index')
@jwt_required()
def index():
    response = {
        "code": 200,
        "message": "Success",
        "data": "index test"
    }
    return jsonify(response)
