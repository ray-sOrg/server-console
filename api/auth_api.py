import bcrypt
import jwt as pyjwt
import requests
from datetime import timedelta
from flask import Blueprint, current_app, jsonify, make_response, redirect, request
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
from model.oidc_login_attempt import OidcLoginAttempt
from model.user import User
from utils.auth_session_utils import (
    ACCESS_TOKEN_LIFETIME,
    REFRESH_TOKEN_LIFETIME,
    max_age_seconds,
    session_is_active,
    session_remaining,
    utc_now,
    ensure_utc,
)
from utils.oidc import APP_TARGETS, authorization_url, digest, random_urlsafe


auth_api_pb = Blueprint('auth_api', __name__)

AUTH_COOKIE_NAMES = (
    'access_token_cookie',
    'csrf_access_token',
    'refresh_token_cookie',
    'csrf_refresh_token',
)
OIDC_STATE_COOKIE = 'console_oidc_state_v2'
LEGACY_OIDC_STATE_COOKIE = 'console_oidc_state'
OIDC_ATTEMPT_LIFETIME = timedelta(minutes=10)


def oidc_setting(name):
    value = current_app.config.get(name)
    if not value:
        raise RuntimeError(f'{name} is not configured')
    return value


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


@auth_api_pb.route('/auth/oidc/login', methods=['GET'])
def oidc_login():
    target_app = request.args.get('app', 'console')
    if target_app not in APP_TARGETS:
        return jsonify({'code': 400, 'message': 'Unknown application', 'data': {}}), 400
    state = random_urlsafe()
    nonce = random_urlsafe()
    verifier = random_urlsafe(64)
    now = utc_now()
    OidcLoginAttempt.query.filter(OidcLoginAttempt.expires_at <= now).delete()
    db.session.add(OidcLoginAttempt(
        state_hash=digest(state), code_verifier=verifier, nonce=nonce,
        target_app=target_app, expires_at=now + OIDC_ATTEMPT_LIFETIME,
    ))
    db.session.commit()
    location = authorization_url(
        oidc_setting('OIDC_ISSUER'), oidc_setting('OIDC_CLIENT_ID'),
        oidc_setting('OIDC_CALLBACK_URL'), state, nonce, verifier,
    )
    response = redirect(location)
    response.set_cookie(
        OIDC_STATE_COOKIE, state, httponly=True,
        secure=current_app.config.get('JWT_COOKIE_SECURE', False),
        samesite='Lax', path='/api/auth/oidc/callback',
        max_age=int(OIDC_ATTEMPT_LIFETIME.total_seconds()),
    )
    # Remove the pre-v2 cookie so stale values cannot win when duplicate
    # cookies with different paths are sent by the browser.
    response.set_cookie(LEGACY_OIDC_STATE_COOKIE, '', expires=0, path='/')
    response.set_cookie(LEGACY_OIDC_STATE_COOKIE, '', expires=0, path='/api/auth/oidc/callback')
    return response


@auth_api_pb.route('/auth/oidc/callback', methods=['GET'])
def oidc_callback():
    state = request.args.get('state', '')
    if not state or state != request.cookies.get(OIDC_STATE_COOKIE):
        return jsonify({'code': 400, 'message': 'Invalid login state', 'data': {}}), 400
    attempt = db.session.get(OidcLoginAttempt, digest(state))
    if not attempt or ensure_utc(attempt.expires_at) <= utc_now():
        return jsonify({'code': 400, 'message': 'Login request expired', 'data': {}}), 400

    try:
        issuer = oidc_setting('OIDC_ISSUER').rstrip('/')
        token_response = requests.post(
            issuer + '/protocol/openid-connect/token', timeout=15,
            data={
                'grant_type': 'authorization_code',
                'code': request.args.get('code', ''),
                'redirect_uri': oidc_setting('OIDC_CALLBACK_URL'),
                'client_id': oidc_setting('OIDC_CLIENT_ID'),
                'client_secret': oidc_setting('OIDC_CLIENT_SECRET'),
                'code_verifier': attempt.code_verifier,
            },
        )
        token_response.raise_for_status()
        id_token = token_response.json()['id_token']
        signing_key = pyjwt.PyJWKClient(
            issuer + '/protocol/openid-connect/certs', timeout=15,
        ).get_signing_key_from_jwt(id_token)
        claims = pyjwt.decode(
            id_token, signing_key.key, algorithms=['RS256'],
            audience=oidc_setting('OIDC_CLIENT_ID'), issuer=issuer,
        )
        if claims.get('nonce') != attempt.nonce:
            raise ValueError('OIDC nonce mismatch')
        required_role, target_url = APP_TARGETS[attempt.target_app]
        roles = claims.get('realm_access', {}).get('roles', [])
        if required_role not in roles:
            db.session.delete(attempt)
            db.session.commit()
            return redirect(target_url + '/?auth_error=forbidden')
        user = User.query.filter_by(oidc_subject=claims['sub']).first()
        if user is None:
            db.session.delete(attempt)
            db.session.commit()
            return redirect(target_url + '/?auth_error=unmapped')

        now = utc_now()
        auth_session = AuthSession(
            user_identity=user.username,
            expires_at=now + REFRESH_TOKEN_LIFETIME,
            last_used_at=now,
        )
        db.session.add(auth_session)
        db.session.delete(attempt)
        db.session.flush()
        access_token, refresh_token, access_lifetime, refresh_lifetime = issue_session_tokens(
            auth_session, now,
        )
        db.session.commit()
        response = redirect(target_url)
        response.set_cookie(
            OIDC_STATE_COOKIE, '', expires=0,
            path='/api/auth/oidc/callback', httponly=True,
        )
        response.set_cookie(LEGACY_OIDC_STATE_COOKIE, '', expires=0, path='/')
        response.set_cookie(LEGACY_OIDC_STATE_COOKIE, '', expires=0, path='/api/auth/oidc/callback')
        set_session_cookies(
            response, access_token, refresh_token,
            access_lifetime, refresh_lifetime,
        )
        return response
    except Exception:
        current_app.logger.exception('OIDC callback failed')
        db.session.rollback()
        OidcLoginAttempt.query.filter_by(state_hash=digest(state)).delete()
        db.session.commit()
        return jsonify({'code': 400, 'message': 'Unified login failed', 'data': {}}), 400


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
