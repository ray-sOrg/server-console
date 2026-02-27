from flask import Blueprint, jsonify, request, make_response
from flask_jwt_extended import (create_access_token, unset_jwt_cookies, set_access_cookies, set_refresh_cookies,
                                create_refresh_token, jwt_required, get_jwt_identity)
from model.user import User
import bcrypt

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
    try:
        password_hash = user.password.encode('utf-8') if isinstance(user.password, str) else user.password
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
            return jsonify({"code": 500, "data": {}, "message": "密码错误"}), 200
    except Exception as e:
        return jsonify({"code": 500, "data": {}, "message": "密码验证失败"}), 200

    # 创建访问令牌
    access_token = create_access_token(identity=user.username)
    refresh_token = create_refresh_token(identity=user.username)
    user_data = {'uuid': user.uid, 'username': user.username, 'role': user.role, 'create_time': user.create_time}
    response = make_response(jsonify({"code": 200, "message": "Success", "token": access_token,
                                     "refresh_token": refresh_token,"data": user_data}), 200)

    # 设置访问令牌和刷新令牌到Cookie
    set_access_cookies(response, access_token)
    set_refresh_cookies(response, refresh_token)
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
    access_token = create_access_token(identity=identity)
    response = jsonify({"code": 200, "message": "token refresh successful", "data": {"token": access_token}})
    set_access_cookies(response, access_token)
    return response
