"""Server-only central refresh credential; never expose it in application JWTs."""
import base64
import hashlib
from datetime import timedelta

import requests
from cryptography.fernet import Fernet
from flask import current_app

from extensions import db
from model.auth_session import AuthSession
from utils.auth_session_utils import ensure_utc, utc_now


class CentralSessionUnavailable(Exception):
    pass


def encrypt_refresh_token(token):
    secret = current_app.config['OIDC_CLIENT_SECRET']
    key = base64.urlsafe_b64encode(hashlib.sha256(('central-session-v1:' + secret).encode()).digest())
    return Fernet(key).encrypt(token.encode()).decode()


def decrypt_refresh_token(token):
    secret = current_app.config['OIDC_CLIENT_SECRET']
    key = base64.urlsafe_b64encode(hashlib.sha256(('central-session-v1:' + secret).encode()).digest())
    return Fernet(key).decrypt(token.encode()).decode()


def central_session_active(session):
    if not current_app.config.get('OIDC_SESSION_ENFORCED', False):
        return True
    if not session.oidc_sid or not session.oidc_refresh_token:
        return False  # Legacy sessions must complete the normal OIDC flow again.
    now = utc_now()
    if session.oidc_checked_at and now - ensure_utc(session.oidc_checked_at) < timedelta(seconds=60):
        return True
    old_token = session.oidc_refresh_token
    try:
        result = requests.post(current_app.config['OIDC_ISSUER'].rstrip('/') + '/protocol/openid-connect/token',
            data={'grant_type': 'refresh_token', 'refresh_token': decrypt_refresh_token(old_token),
                  'client_id': current_app.config['OIDC_CLIENT_ID'], 'client_secret': current_app.config['OIDC_CLIENT_SECRET']},
            timeout=8)
        payload = result.json()
    except Exception:
        raise CentralSessionUnavailable() from None
    if result.status_code == 400 and payload.get('error') == 'invalid_grant':
        AuthSession.query.filter_by(session_id=session.session_id, oidc_refresh_token=old_token).update({'revoked_at': now})
        db.session.commit()
        return False
    if result.status_code != 200 or not isinstance(payload.get('refresh_token'), str):
        raise CentralSessionUnavailable()
    # Do not hold a DB row lock over a network request, nor revive a session
    # concurrently revoked by a signed back-channel notification.
    updated = AuthSession.query.filter_by(session_id=session.session_id, oidc_refresh_token=old_token, revoked_at=None).update({
        'oidc_refresh_token': encrypt_refresh_token(payload['refresh_token']), 'oidc_checked_at': now,
    })
    db.session.commit()
    if updated:
        return True
    db.session.expire_all()
    latest = AuthSession.query.filter_by(session_id=session.session_id).first()
    return bool(latest and latest.revoked_at is None and latest.oidc_checked_at and now - ensure_utc(latest.oidc_checked_at) < timedelta(seconds=60))
