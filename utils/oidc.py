import base64
import hashlib
import secrets
from urllib.parse import urlencode


APP_TARGETS = {
    'console': ('app-console', 'https://console.tt829.cn'),
    'weight': ('app-weight', 'https://weight.tt829.cn'),
}


def digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def random_urlsafe(size=32):
    return secrets.token_urlsafe(size)


def pkce_challenge(verifier):
    value = hashlib.sha256(verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def authorization_url(issuer, client_id, redirect_uri, state, nonce, verifier):
    query = urlencode({
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid profile email',
        'state': state,
        'nonce': nonce,
        'code_challenge': pkce_challenge(verifier),
        'code_challenge_method': 'S256',
    })
    return issuer.rstrip('/') + '/protocol/openid-connect/auth?' + query

