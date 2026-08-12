import bcrypt
from flask import Blueprint, current_app, jsonify, make_response, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
    get_jwt_identity,
    set_access_cookies,
    set_refresh_cookies,
    unset_jwt_cookies,
    verify_jwt_in_request,
    jwt_required,
)

from extensions import db
from model.auth_session import AuthSession
from model.user import User
from utils.auth_session_utils import (
    ACCESS_TOKEN_LIFETIME,
    REFRESH_TOKEN_LIFETIME,
    max_age_seconds,
    session_is_active,
    session_remaining,
    utc_now,
)


auth_api_pb = Blueprint('auth_api', __name__)

AUTH_COOKIE_NAMES = (
    'access_token_cookie',
    'csrf_access_token',
    'refresh_token_cookie',
    'csrf_refresh_token',
)


def clear_legacy_root_cookies(response):
    """Remove host-only and old root-path cookies from earlier releases."""
    configured_domain = current_app.config.get('JWT_COOKIE_DOMAIN')
    cookie_secure = current_app.config.get('JWT_COOKIE_SECURE', False)
    cookie_domains = (None, configured_domain) if configured_domain else (None,)
    for cookie_domain in cookie_domains:
        for cookie_name in AUTH_COOKIE_NAMES:
            response.set_cookie(
                cookie_name,
                value='',
                expires=0,
                path='/',
                domain=cookie_domain,
                secure=cookie_secure,
                httponly=cookie_name.endswith('_token_cookie'),
                samesite='Lax',
            )


def issue_session_tokens(auth_session, now=None):
    current_time = now or utc_now()
    remaining = session_remaining(auth_session, current_time)
    if remaining.total_seconds() <= 0:
        raise ValueError('Login session has expired')

    access_lifetime = min(ACCESS_TOKEN_LIFETIME, remaining)
    claims = {'sid': auth_session.session_id}
    access_token = create_access_token(
        identity=auth_session.user_identity,
        additional_claims=claims,
        expires_delta=access_lifetime,
    )
    refresh_token = create_refresh_token(
        identity=auth_session.user_identity,
        additional_claims=claims,
        expires_delta=remaining,
    )
    new_refresh_jti = decode_token(refresh_token)['jti']
    auth_session.previous_refresh_jti = auth_session.current_refresh_jti
    auth_session.current_refresh_jti = new_refresh_jti
    auth_session.refresh_rotated_at = current_time
    auth_session.last_used_at = current_time
    return access_token, refresh_token, access_lifetime, remaining


def set_session_cookies(response, access_token, refresh_token, access_lifetime, refresh_lifetime):
    set_access_cookies(
        response,
        access_token,
        max_age=max_age_seconds(access_lifetime),
    )
    set_refresh_cookies(
        response,
        refresh_token,
        max_age=max_age_seconds(refresh_lifetime),
    )


@auth_api_pb.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({'code': 500, 'data': {}, 'message': '未找到用户'}), 200

    try:
        password_hash = user.password.encode('utf-8') if isinstance(user.password, str) else user.password
        if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
            return jsonify({'code': 500, 'data': {}, 'message': '密码错误'}), 200
    except Exception:
        return jsonify({'code': 500, 'data': {}, 'message': '密码验证失败'}), 200

    now = utc_now()
    auth_session = AuthSession(
        user_identity=user.username,
        expires_at=now + REFRESH_TOKEN_LIFETIME,
        last_used_at=now,
    )
    db.session.add(auth_session)
    db.session.flush()
    access_token, refresh_token, access_lifetime, refresh_lifetime = issue_session_tokens(
        auth_session,
        now,
    )
    db.session.commit()

    user_data = {
        'uuid': user.uid,
        'username': user.username,
        'displayName': user.display_name,
        'role': user.role,
        'heightCm': user.height_cm,
        'birthDate': user.birth_date.isoformat() if user.birth_date else None,
        'create_time': user.create_time,
    }
    response = make_response(jsonify({
        'code': 200,
        'message': 'Success',
        'data': user_data,
    }), 200)
    clear_legacy_root_cookies(response)
    set_session_cookies(
        response,
        access_token,
        refresh_token,
        access_lifetime,
        refresh_lifetime,
    )
    return response


@auth_api_pb.route('/auth/logout', methods=['POST'])
def logout():
    try:
        verify_jwt_in_request(refresh=True)
        jwt_payload = get_jwt()
        auth_session = AuthSession.query.filter_by(
            session_id=jwt_payload.get('sid'),
            user_identity=get_jwt_identity(),
        ).first()
        if auth_session:
            auth_session.revoke(utc_now())
            db.session.commit()
    except Exception:
        db.session.rollback()

    response = jsonify({'code': 200, 'message': 'logout successful', 'data': {}})
    unset_jwt_cookies(response)
    clear_legacy_root_cookies(response)
    return response


@auth_api_pb.route('/auth/token/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    jwt_payload = get_jwt()
    auth_session = AuthSession.query.filter_by(
        session_id=jwt_payload.get('sid'),
        user_identity=identity,
    ).first()
    now = utc_now()
    if not session_is_active(auth_session, now):
        return jsonify({'code': 5005, 'message': 'Login session is no longer active', 'data': {}}), 200

    access_token, refresh_token, access_lifetime, refresh_lifetime = issue_session_tokens(
        auth_session,
        now,
    )
    db.session.commit()
    response = jsonify({
        'code': 200,
        'message': 'token refresh successful',
        'data': {},
    })
    set_session_cookies(
        response,
        access_token,
        refresh_token,
        access_lifetime,
        refresh_lifetime,
    )
    return response
