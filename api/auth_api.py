from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token
from model.user import User
from werkzeug.security import check_password_hash

auth_api_pb = Blueprint('auth_api', __name__)


@auth_api_pb.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"code": 401, "message": "Invalid credentials"}), 200

    access_token = create_access_token(identity=user.username)
    return jsonify({"code": 200, "message": "Success", "data": {"access_token": access_token}}), 200
