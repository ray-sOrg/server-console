from datetime import datetime, timezone
from flask import Blueprint, g, jsonify, request
from model.user import User
from extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from utils import keycloak_admin
from utils.authorization import admin_required, forbidden, super_admin_required

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


def serialize_central_user(identity, local_user=None):
    created_timestamp = identity.get('createdTimestamp')
    created_time = None
    if isinstance(created_timestamp, (int, float)):
        created_time = datetime.fromtimestamp(
            created_timestamp / 1000, tz=timezone.utc,
        ).isoformat()
    display_name = ' '.join(filter(None, (
        identity.get('firstName'), identity.get('lastName'),
    ))) or (local_user.display_name if local_user else None)
    return {
        'uuid': local_user.uid if local_user else identity['id'],
        'oidcSubject': identity['id'],
        'username': identity.get('username', ''),
        'displayName': display_name,
        'email': identity.get('email'),
        'enabled': identity.get('enabled', False),
        'emailVerified': identity.get('emailVerified', False),
        'requiredActions': identity.get('requiredActions') or [],
        'role': local_user.role if local_user else None,
        'mapped': local_user is not None,
        'create_time': created_time,
    }


def central_error(exc):
    return jsonify({
        'code': 503,
        'message': str(exc),
        'data': {},
    }), 503


@user_api_pb.route('/user/list', methods=['GET'])
@admin_required
def get_user_list():
    page_number = max(request.args.get('pageNumber', 1, type=int), 1)
    page_size = min(max(request.args.get('pageSize', 10, type=int), 1), 100)
    keyword = request.args.get('keyword', '', type=str).strip()

    try:
        identities = keycloak_admin.list_users(keyword)
        subjects = [identity['id'] for identity in identities]
        local_users = User.query.filter(User.oidc_subject.in_(subjects)).all() if subjects else []
        local_by_subject = {user.oidc_subject: user for user in local_users}
        local_by_name = {
            user.username: user
            for user in User.query.filter(User.username.in_([
                identity.get('username') for identity in identities
            ])).all()
        } if identities else {}
        users = [
            serialize_central_user(
                identity,
                local_by_subject.get(identity['id'])
                or local_by_name.get(identity.get('username')),
            )
            for identity in identities
        ]
        users.sort(key=lambda item: item['username'].lower())
        start = (page_number - 1) * page_size
        return jsonify({
            'code': 200,
            'message': 'Success',
            'data': users[start:start + page_size],
            'total': len(users),
        }), 200
    except keycloak_admin.KeycloakAdminError as exc:
        return central_error(exc)


def requested_identity():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('oidcSubject'), str):
        return None, (jsonify({
            'code': 400,
            'message': '请选择统一账号',
            'data': {},
        }), 200)
    try:
        return keycloak_admin.get_user(data['oidcSubject']), None
    except keycloak_admin.KeycloakAdminError as exc:
        return None, central_error(exc)


@user_api_pb.route('/user/password/reset', methods=['POST'])
@super_admin_required
def reset_user_password():
    identity, error = requested_identity()
    if error:
        return error
    password = keycloak_admin.generate_temporary_password()
    try:
        keycloak_admin.require_password_update(
            identity['id'], identity.get('requiredActions'),
        )
        keycloak_admin.reset_temporary_password(identity['id'], password)
        keycloak_admin.logout_user(identity['id'])
    except keycloak_admin.KeycloakAdminError as exc:
        return central_error(exc)
    return jsonify({
        'code': 200,
        'message': '临时密码已生成，下次登录必须修改密码',
        'data': {
            'username': identity.get('username', ''),
            'temporaryPassword': password,
        },
    }), 200


@user_api_pb.route('/user/status/update', methods=['POST'])
@super_admin_required
def update_user_status():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get('enabled'), bool):
        return jsonify({'code': 400, 'message': '账号状态无效', 'data': {}}), 200
    identity, error = requested_identity()
    if error:
        return error
    actor_subject = g.console_actor.oidc_subject
    if data['enabled'] is False and (
        identity['id'] == actor_subject
        or identity.get('username') == g.console_actor.username
    ):
        return forbidden('不能停用当前登录账号')
    try:
        keycloak_admin.set_user_enabled(identity['id'], data['enabled'])
        if not data['enabled']:
            keycloak_admin.logout_user(identity['id'])
    except keycloak_admin.KeycloakAdminError as exc:
        return central_error(exc)
    return jsonify({
        'code': 200,
        'message': '账号已启用' if data['enabled'] else '账号已停用',
        'data': {
            'oidcSubject': identity['id'],
            'enabled': data['enabled'],
        },
    }), 200


@user_api_pb.route('/user/sessions/logout', methods=['POST'])
@super_admin_required
def logout_user_sessions():
    identity, error = requested_identity()
    if error:
        return error
    try:
        keycloak_admin.logout_user(identity['id'])
    except keycloak_admin.KeycloakAdminError as exc:
        return central_error(exc)
    return jsonify({
        'code': 200,
        'message': f"已注销 {identity.get('username', '')} 的全部会话",
        'data': {'oidcSubject': identity['id']},
    }), 200


@user_api_pb.route('/user/delete', methods=['POST'])
@admin_required
def delete_user():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'code': 400, 'message': '请提供用户信息', 'data': {}}), 200
    uuid = data.get('uuid', '')
    if not uuid:
        return jsonify({"code": 500, "message": "Bad Request", "data": "Missing uuid"}), 200

    try:
        user = User.query.filter_by(uid=uuid).first()
        if not user:
            return jsonify({"code": 500, "message": "User not found", "data": {}}), 200

        if user.id == g.console_actor.id:
            return forbidden('不能删除当前登录账号')
        if user.role != 'user' and g.console_actor.role != 'super_admin':
            return forbidden('仅超级管理员可删除管理员账号')

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
