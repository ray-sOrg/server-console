from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import (create_access_token, unset_jwt_cookies, set_access_cookies, create_refresh_token,
                                jwt_required, get_jwt_identity)
from model.user import User
from werkzeug.security import check_password_hash

auth_api_pb = Blueprint('auth_api', __name__)


@auth_api_pb.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # 查找用户
    user = User.query.filter_by(username=username).first()

    # 用户不存在的情况
    if not user:
        return jsonify({"code": 500, "data": {}, "message": "未找到用户"}), 200

    # 用户存在但密码不正确的情况
    if not check_password_hash(user.password, password):
        return jsonify({"code": 500, "data": {}, "message": "密码错误"}), 200

    # 创建访问令牌
    access_token = create_access_token(identity=user.username)
    refresh_token = create_refresh_token(identity=user.username)
    user_data = {'uuid': user.uid, 'username': user.username, 'role': user.role, 'create_time': user.create_time}
    response = make_response(jsonify({"code": 200, "message": "Success", "token": access_token,
                                     "refresh_token": refresh_token,"data": user_data}), 200)

    # 设置访问令牌到 Cookie
    set_access_cookies(response, access_token)
    return response


@auth_api_pb.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"code": 200, "message": "logout successful", "data": {}})
    unset_jwt_cookies(response)
    return response


# 使用 `refresh=True` 参数，确保只有刷新令牌可以访问这个路由
@auth_api_pb.route("/token/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    token = create_access_token(identity=identity)
    return jsonify({"code": 200, "message": "token refresh successful", "data": {token: token}})
