import jwt as pyjwt
import requests
import secrets
import json
from datetime import timedelta
from urllib.parse import urlencode, urlsplit
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
    max_age_seconds,
    session_is_active,
    session_remaining,
    utc_now,
    ensure_utc,
)
from utils.oidc import APP_TARGETS, authorization_url, digest, random_urlsafe
from utils.oidc_logout import validate_logout_token
from utils.central_session import encrypt_refresh_token


auth_api_pb = Blueprint('auth_api', __name__)

AUTH_COOKIE_NAMES = (
    'access_token_cookie',
    'csrf_access_token',
    'refresh_token_cookie',
    'csrf_refresh_token',
)
OIDC_STATE_COOKIE = 'console_oidc_state_v3'
LEGACY_OIDC_STATE_COOKIES = ('console_oidc_state', 'console_oidc_state_v2')
OIDC_ATTEMPT_LIFETIME = timedelta(minutes=10)


def oidc_setting(name):
    value = current_app.config.get(name)
    if not value:
        raise RuntimeError(f'{name} is not configured')
    return value


def clear_legacy_root_cookies(response):
    """Remove old host-only/domain variants before writing canonical cookies."""
    configured_domain = current_app.config.get('JWT_COOKIE_DOMAIN')
    cookie_secure = current_app.config.get('JWT_COOKIE_SECURE', False)
    cookie_domains = (None, configured_domain) if configured_domain else (None,)
    for cookie_domain in cookie_domains:
        for cookie_name in AUTH_COOKIE_NAMES:
            for cookie_path in ('/', '/api/auth'):
                response.set_cookie(
                    cookie_name,
                    value='',
                    expires=0,
                    path=cookie_path,
                    domain=cookie_domain,
                    secure=cookie_secure,
                    httponly=cookie_name.endswith('_token_cookie'),
                    samesite='Lax',
                )


def clear_oidc_state_cookies(response):
    response.delete_cookie(OIDC_STATE_COOKIE, path='/api/auth/oidc/callback')
    configured_domain = current_app.config.get('JWT_COOKIE_DOMAIN')
    domains = (None, configured_domain) if configured_domain else (None,)
    for domain in domains:
        for name in LEGACY_OIDC_STATE_COOKIES:
            for path in ('/', '/api/auth/oidc/callback'):
                response.delete_cookie(name, path=path, domain=domain)


def oidc_failure(target_app, reason):
    # The app and reason are server-selected; never redirect to a request URL.
    target_url = APP_TARGETS[target_app][1]
    path = '/login' if target_app == 'console' else '/'
    current_app.logger.warning('OIDC login rejected: app=%s reason=%s', target_app, reason)
    response = silent_sso_result(target_app, False) if request.args.get('state', '').startswith('silent.') else redirect(target_url + path + '?' + urlencode({'auth_error': reason}))
    if not request.args.get('state', '').startswith('silent.'):
        clear_oidc_state_cookies(response)
    return response


def silent_sso_result(target_app, authenticated):
    origin = APP_TARGETS[target_app][1].rstrip('/')
    nonce = secrets.token_urlsafe(18)
    payload = json.dumps({'type': 'tt829:sso', 'authenticated': authenticated})
    response = make_response(f'<!doctype html><script nonce="{nonce}">parent.postMessage({payload},{json.dumps(origin)});</script>')
    response.headers['Content-Type'] = 'text/html; charset=utf-8'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Content-Security-Policy'] = f"default-src 'none'; script-src 'nonce-{nonce}'; frame-ancestors {origin}"
    response.delete_cookie(OIDC_STATE_COOKIE + '_silent_' + target_app, path='/api/auth/oidc/callback')
    return response


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
    # Older SPA builds used a same-origin reverse proxy. Establish browser
    # binding on the actual callback host before allocating a login attempt.
    callback = urlsplit(oidc_setting('OIDC_CALLBACK_URL'))
    canonical_origin = callback.scheme + '://' + callback.netloc
    if request.host.lower() != callback.netloc.lower():
        return redirect(canonical_origin + '/api/auth/oidc/login?' + urlencode({'app': target_app}))
    silent = request.args.get('silent') == '1'
    state = ('silent.' + target_app + '.' if silent else '') + random_urlsafe()
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
    if silent:
        response.headers['Location'] = location + '&prompt=none'
    else:
        clear_oidc_state_cookies(response)
    response.set_cookie(
        OIDC_STATE_COOKIE + ('_silent_' + target_app if silent else ''), state, httponly=True,
        secure=current_app.config.get('JWT_COOKIE_SECURE', False),
        samesite='Lax', path='/api/auth/oidc/callback',
        max_age=int(OIDC_ATTEMPT_LIFETIME.total_seconds()),
    )
    return response


@auth_api_pb.route('/auth/oidc/callback', methods=['GET'])
def oidc_callback():
    state = request.args.get('state', '')
    silent_app = state.split('.')[1] if state.startswith('silent.') and len(state.split('.')) == 3 else None
    cookie_state = request.cookies.get(OIDC_STATE_COOKIE + ('_silent_' + silent_app if silent_app in APP_TARGETS else ''))
    if not state or not cookie_state or not secrets.compare_digest(state, cookie_state):
        return jsonify({'code': 400, 'message': 'Invalid login state', 'data': {}}), 400
    attempt = db.session.get(OidcLoginAttempt, digest(state))
    if not attempt or ensure_utc(attempt.expires_at) <= utc_now():
        return jsonify({'code': 400, 'message': 'Login request expired', 'data': {}}), 400
    target_app = attempt.target_app
    nonce = attempt.nonce
    verifier = attempt.code_verifier
    # Claim once before exchanging the code, including across worker processes.
    claimed = OidcLoginAttempt.query.filter_by(state_hash=digest(state)).delete()
    db.session.commit()
    if claimed != 1:
        return jsonify({'code': 400, 'message': 'Login request expired', 'data': {}}), 400
    if request.args.get('error') or not request.args.get('code'):
        return oidc_failure(target_app, 'failed')

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
                'code_verifier': verifier,
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
            options={'require': ['sub', 'exp', 'iat', 'iss', 'aud', 'nonce']},
        )
        if claims.get('nonce') != nonce:
            raise ValueError('OIDC nonce mismatch')
        if not isinstance(claims.get('sid'), str) or not claims['sid']:
            raise ValueError('Missing OIDC session')
        required_role, target_url = APP_TARGETS[target_app]
        roles = claims.get('realm_access', {}).get('roles', [])
        if required_role not in roles:
            return oidc_failure(target_app, 'forbidden')
        user = User.query.filter_by(oidc_subject=claims['sub']).first()
        if user is None:
            return oidc_failure(target_app, 'unmapped')

        now = utc_now()
        auth_session = AuthSession(
            user_identity=user.username,
            oidc_sid=claims.get('sid'),
            oidc_subject=claims['sub'],
            oidc_refresh_token=encrypt_refresh_token(token_response.json()['refresh_token']) if token_response.json().get('refresh_token') else None,
            oidc_checked_at=now,
            expires_at=now + timedelta(days=30),
            last_used_at=now,
        )
        db.session.add(auth_session)
        db.session.flush()
        access_token, refresh_token, access_lifetime, refresh_lifetime = issue_session_tokens(
            auth_session, now,
        )
        db.session.commit()
        response = silent_sso_result(target_app, True) if silent_app else redirect(target_url)
        if not silent_app:
            clear_oidc_state_cookies(response)
        clear_legacy_root_cookies(response)
        set_session_cookies(
            response, access_token, refresh_token,
            access_lifetime, refresh_lifetime,
        )
        return response
    except Exception as exc:
        # Avoid logging authorization codes, token payloads, or provider URLs
        # from exception messages; record only the exception class.
        current_app.logger.warning('OIDC callback failed: error_type=%s', type(exc).__name__)
        db.session.rollback()
        return oidc_failure(target_app, 'failed')


@auth_api_pb.route('/auth/oidc/backchannel-logout', methods=['POST'])
def oidc_backchannel_logout():
    token = request.form.get('logout_token', '')
    if not token or len(token) > 16384:
        return jsonify({'message': 'Invalid logout token'}), 400
    try:
        issuer = oidc_setting('OIDC_ISSUER').rstrip('/')
        key = pyjwt.PyJWKClient(issuer + '/protocol/openid-connect/certs', timeout=15).get_signing_key_from_jwt(token)
        claims = validate_logout_token(token, key.key, issuer, oidc_setting('OIDC_CLIENT_ID'))
        sessions = AuthSession.query.filter_by(oidc_sid=claims['sid'])
        if claims.get('sub'):
            sessions = sessions.filter_by(oidc_subject=claims['sub'])
        sessions.filter(AuthSession.revoked_at.is_(None)).update({'revoked_at': utc_now()})
        db.session.commit()
        return '', 200, {'Cache-Control': 'no-store'}
    except Exception as exc:
        db.session.rollback()
        current_app.logger.warning('OIDC logout rejected: %s', type(exc).__name__)
        return jsonify({'message': 'Invalid logout token'}), 400


@auth_api_pb.route('/auth/logout', methods=['POST'])
def logout():
    unified = request.args.get('unified') == '1'
    target_app = request.args.get('app', 'console')
    if unified and target_app not in APP_TARGETS:
        return jsonify({'message': 'Unknown application'}), 400
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
        if unified:
            return jsonify({'message': 'Logout requires a valid session and CSRF token'}), 401

    data = {}
    if unified:
        target_url = APP_TARGETS[target_app][1] + ('/login' if target_app == 'console' else '/')
        data['logoutUrl'] = oidc_setting('OIDC_ISSUER').rstrip('/') + '/protocol/openid-connect/logout?' + urlencode({
            'client_id': oidc_setting('OIDC_CLIENT_ID'),
            'post_logout_redirect_uri': target_url,
        })
    response = jsonify({'code': 200, 'message': 'logout successful', 'data': data})
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
