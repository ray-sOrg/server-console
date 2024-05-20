import time
from flask import Blueprint, jsonify, request
from model.user import User
from extensions import db


user_api_pb = Blueprint('user_api', __name__)


@user_api_pb.route('/user/add', methods=['POST'])
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


@user_api_pb.route('/user/list', methods=['GET'])
def get_user_list():
    page_number = request.args.get('pageNumber', 1, type=int)
    page_size = request.args.get('pageSize', 10, type=int)
    keyword = request.args.get('keyword', '', type=str)

    try:
        # 构造查询
        query = User.query.order_by(User.create_time.desc())
        if keyword:
            query = query.filter(User.username.ilike(f"%{keyword}%"))
        users = query.paginate(page=page_number, per_page=page_size, error_out=False)
        user_list = [{'uuid': user.uid, 'username': user.username, 'role': user.role, 'create_time': user.create_time} for user in users.items]
        total = users.total
        # 模拟延迟
        time.sleep(0.35)
        return jsonify({"code": 200, "message": "Success", "data": user_list, "total": total}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@user_api_pb.route('/user/delete', methods=['POST'])
def delete_user():
    data = request.json
    uuid = data.get('uuid', '')
    if not uuid:
        return jsonify({"code": 500, "message": "Bad Request", "data": "Missing uuid"}), 200

    try:
        user = User.query.filter_by(uid=uuid).first()
        if not user:
            return jsonify({"code": 500, "message": "User not found", "data": {}}), 200

        db.session.delete(user)
        db.session.commit()

        return jsonify({"code": 200, "message": "Success", "data": {"uuid": uuid}}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200

