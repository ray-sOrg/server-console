from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import create_access_token
from model.user import User
from werkzeug.security import check_password_hash
from flask_jwt_extended import jwt_required, get_jwt_identity


auth_api_pb = Blueprint('auth_api', __name__)


@auth_api_pb.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # 查找用户
    user = User.query.filter_by(username=username).first()
    print(f'______-{user}')

    # 用户不存在的情况
    if not user:
        return jsonify({"code": 500, "data": {}, "message": "未找到用户"}), 200

    # 用户存在但密码不正确的情况
    print(f'1______-{password}')
    print(f'2______-{user.password}')
    if not check_password_hash(user.password, password):
        return jsonify({"code": 500, "data": {}, "message": "密码错误"}), 200

    # 创建访问令牌
    access_token = create_access_token(identity=user.username)
    user_data = {'uuid': user.uid, 'username': user.username, 'role': user.role, 'create_time': user.create_time}
    response = make_response(jsonify({"code": 200, "message": "Success", "token": access_token, "data": user_data}), 200)

    # 设置访问令牌到 Cookie
    response.set_cookie('token', access_token, httponly=True)
    return response
