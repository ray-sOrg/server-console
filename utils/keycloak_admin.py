"""Small Keycloak Admin API client using the Console OIDC service account."""
import secrets
import string
from urllib.parse import urlsplit

import requests
from flask import current_app


class KeycloakAdminError(Exception):
    pass


def _settings():
    issuer = current_app.config.get('OIDC_ISSUER', '').rstrip('/')
    client_id = current_app.config.get('OIDC_CLIENT_ID', '')
    client_secret = current_app.config.get('OIDC_CLIENT_SECRET', '')
    parts = urlsplit(issuer)
    path_parts = parts.path.rstrip('/').split('/')
    if not issuer or not client_id or not client_secret or len(path_parts) < 3:
        raise KeycloakAdminError('统一账号管理服务尚未配置')
    realm = path_parts[-1]
    origin = f'{parts.scheme}://{parts.netloc}'
    return issuer, origin, realm, client_id, client_secret


def _access_token():
    issuer, _, _, client_id, client_secret = _settings()
    try:
        response = requests.post(
            issuer + '/protocol/openid-connect/token',
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret,
            },
            timeout=10,
        )
        response.raise_for_status()
        token = response.json().get('access_token')
    except (requests.RequestException, ValueError):
        raise KeycloakAdminError('统一账号服务暂时不可用') from None
    if not isinstance(token, str) or not token:
        raise KeycloakAdminError('统一账号服务返回了无效凭据')
    return token


def _request(method, path, *, json=None, params=None):
    _, origin, realm, _, _ = _settings()
    try:
        response = requests.request(
            method,
            f'{origin}/admin/realms/{realm}/{path.lstrip("/")}',
            headers={'Authorization': 'Bearer ' + _access_token()},
            json=json,
            params=params,
            timeout=12,
        )
        response.raise_for_status()
        return response.json() if response.content else None
    except (requests.RequestException, ValueError):
        raise KeycloakAdminError('统一账号服务请求失败') from None


def list_users(search=''):
    params = {'max': 500, 'briefRepresentation': 'false'}
    if search:
        params['search'] = search
    users = _request('GET', 'users', params=params)
    if not isinstance(users, list):
        raise KeycloakAdminError('统一账号服务返回了无效用户列表')
    return [user for user in users if not user.get('serviceAccountClientId')]


def get_user(user_id):
    user = _request('GET', f'users/{user_id}')
    if not isinstance(user, dict) or not user.get('id'):
        raise KeycloakAdminError('统一账号服务返回了无效用户')
    return user


def reset_temporary_password(user_id, password):
    _request('PUT', f'users/{user_id}/reset-password', json={
        'type': 'password',
        'value': password,
        'temporary': True,
    })


def set_user_enabled(user_id, enabled):
    _request('PUT', f'users/{user_id}', json={'enabled': enabled})


def logout_user(user_id):
    _request('POST', f'users/{user_id}/logout')


def generate_temporary_password():
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    password = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice('!@#$%^&*'),
    ]
    password.extend(secrets.choice(alphabet) for _ in range(20))
    secrets.SystemRandom().shuffle(password)
    return ''.join(password)
