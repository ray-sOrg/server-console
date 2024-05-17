from flask import Blueprint, jsonify, request
from model.user import User
from extensions import db

user_pb = Blueprint('user_api', __name__)


@user_pb.route('/user/add', methods=['POST'])
def add_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')

    # 检查是否提供了所有必要的数据
    if not username or not password or not role:
        return jsonify({"code": 500, "message": "Bad Request", "data": "Missing required fields"}), 200

    # 检查用户名是否唯一
    if User.query.filter_by(username=username).first():
        return jsonify({"code": 500, "message": "User already exists", "data": "A user with that username already exists"}), 200

    # 检查role是否在允许的值范围内
    if role not in ('super_admin', 'admin', 'user'):
        return jsonify({"code": 500, "message": "Bad Request", "data": "Invalid role specified"}), 200

    # 创建并添加新用户
    new_user = User(username=username, password=password, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"code": 200, "message": "Success", "data": {"user_id": new_user.uid}}), 200
