import time
from datetime import datetime
from flask import Blueprint, jsonify, request
from model.user import User
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash

user_api_pb = Blueprint('user_api', __name__)


def serialize_user(user):
    return {
        "uuid": user.uid,
        "username": user.username,
        "displayName": user.display_name,
        "role": user.role,
        "heightCm": user.height_cm,
        "birthDate": user.birth_date.isoformat() if user.birth_date else None,
        "create_time": user.create_time
    }


@user_api_pb.route('/user/add', methods=['POST'])
@jwt_required()
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
    # 使用 generate_password_hash 函数将密码哈希化
    password_hashed = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, password=password_hashed, role=role)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"code": 200, "message": "Success", "data": {"user_id": new_user.uid}}), 200


@user_api_pb.route('/user/list', methods=['GET'])
@jwt_required()
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
@jwt_required()
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


@user_api_pb.route('/user/login/info', methods=['GET'])
@jwt_required()
def login_info_user():
    try:
        # 从请求上下文中获取当前用户身份
        current_user_identity = get_jwt_identity()
        # 查询用户信息
        user = User.query.filter_by(username=current_user_identity).first()
        if not user:
            return jsonify({"code": 500, "message": "User not found", "data": {}}), 200
        # 构造返回的用户信息
        return jsonify({"code": 200, "message": "Success", "data": serialize_user(user)}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@user_api_pb.route('/user/profile/update', methods=['POST'])
@jwt_required()
def update_profile_user():
    data = request.json or {}
    display_name = data.get('displayName')
    height_cm = data.get('heightCm')
    birth_date = data.get('birthDate')

    if display_name is None and height_cm is None and birth_date is None:
        return jsonify({"code": 500, "message": "displayName, heightCm or birthDate is required", "data": {}}), 200

    if display_name is not None:
        display_name = str(display_name).strip()
        if not display_name:
            return jsonify({"code": 500, "message": "displayName is required", "data": {}}), 200
        if len(display_name) > 100:
            return jsonify({"code": 500, "message": "displayName must be 100 characters or less", "data": {}}), 200

    if height_cm is not None:
        try:
            height_cm = int(height_cm)
        except (TypeError, ValueError):
            return jsonify({"code": 500, "message": "heightCm must be a number", "data": {}}), 200

        if height_cm < 80 or height_cm > 250:
            return jsonify({"code": 500, "message": "heightCm must be between 80 and 250", "data": {}}), 200

    parsed_birth_date = None
    if birth_date:
        try:
            parsed_birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return jsonify({"code": 500, "message": "birthDate must be YYYY-MM-DD", "data": {}}), 200

    try:
        current_user_identity = get_jwt_identity()
        user = User.query.filter_by(username=current_user_identity).first()
        if not user:
            return jsonify({"code": 500, "message": "User not found", "data": {}}), 200

        if display_name is not None:
            user.display_name = display_name
        if height_cm is not None:
            user.height_cm = height_cm
        if birth_date is not None:
            user.birth_date = parsed_birth_date
        db.session.commit()
        return jsonify({"code": 200, "message": "Success", "data": serialize_user(user)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200
