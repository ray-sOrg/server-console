from flask import Blueprint, jsonify, render_template
from flask_jwt_extended import jwt_required
from oss_utils import OSSClient
from config import access_key_id, access_key_secret, endpoint, bucket_name

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


@index_api_pb.route('/asyncOss')
@jwt_required()
def readOss():
    oss_client = OSSClient(access_key_id, access_key_secret, endpoint, bucket_name)
    files = oss_client.list_files()
    if files:
        response = jsonify({"code": 200, "message": "logout successful", "data": {}})
    else:
        response = jsonify({"code": 500, "message": "logout failed", "data": {}})
    return response
