from flask import Flask, Blueprint, jsonify

index_pb = Blueprint('index_api', __name__)


@index_pb.route('/index')
def index():
    response = {
        "code": 200,
        "message": "Success",
        "data": "index test"
    }
    return jsonify(response)
