"""OIDC callback and cookie-session integration without external services."""
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

import bcrypt
import jwt as pyjwt
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import decode_token

from api import auth_api, user_api
from extensions import db, jwt
from model.auth_session import AuthSession
from model.oidc_login_attempt import OidcLoginAttempt
from model.user import User
from utils.auth_session_utils import utc_now
from utils.jwt_errors import register_jwt_errors


API_ORIGIN = 'https://api.tt829.cn'
CONSOLE_ORIGIN = 'https://console.tt829.cn'
WEIGHT_ORIGIN = 'https://weight.tt829.cn'
CALLBACK_PATH = '/api/auth/oidc/callback'


class OidcAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.password_hash = bcrypt.hashpw(b'test-password', bcrypt.gensalt()).decode()

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            JWT_SECRET_KEY='offline-test-key-at-least-32-characters',
            JWT_TOKEN_LOCATION=['cookies'],
            JWT_COOKIE_DOMAIN='.tt829.cn',
            JWT_COOKIE_SECURE=True,
            JWT_COOKIE_SAMESITE='Lax',
            JWT_REFRESH_COOKIE_PATH='/api/auth',
            JWT_REFRESH_CSRF_COOKIE_PATH='/',
            OIDC_ISSUER='https://auth.example/realms/test',
            OIDC_CLIENT_ID='server-console',
            OIDC_CLIENT_SECRET='offline-client-secret',
            OIDC_CALLBACK_URL=API_ORIGIN + CALLBACK_PATH,
        )
        CORS(self.app, supports_credentials=True, origins=[CONSOLE_ORIGIN, WEIGHT_ORIGIN])
        db.init_app(self.app)
        jwt.init_app(self.app)
        register_jwt_errors()
        self.app.register_blueprint(auth_api.auth_api_pb, url_prefix='/api')
        self.app.register_blueprint(user_api.user_api_pb, url_prefix='/api')
        self.context = self.app.app_context()
        self.context.push()
        for model in (User, AuthSession, OidcLoginAttempt):
            model.__table__.create(db.engine)
        db.session.add(User(username='tangtao', password=self.password_hash,
                            oidc_subject='identity-tangtao', role='admin'))
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def begin(self, app='console'):
        response = self.client.get('/api/auth/oidc/login?app=' + app, base_url=API_ORIGIN)
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.location).query)
        return query['state'][0], query['nonce'][0], response

    def test_silent_sso_uses_isolated_state_and_never_redirects_parent(self):
        manual_state, _, _ = self.begin()
        response = self.client.get('/api/auth/oidc/login?app=console&silent=1', base_url=API_ORIGIN)
        query = parse_qs(urlsplit(response.location).query)
        self.assertEqual(query['prompt'], ['none'])
        self.assertTrue(query['state'][0].startswith('silent.console.'))
        self.assertEqual(self.client.get_cookie(auth_api.OIDC_STATE_COOKIE, domain='api.tt829.cn', path=CALLBACK_PATH).value, manual_state)
        result = self.client.get(CALLBACK_PATH, query_string={'state': query['state'][0], 'error': 'login_required'}, base_url=API_ORIGIN)
        self.assertEqual(result.status_code, 200)
        self.assertNotIn('Location', result.headers)
        self.assertIn('"authenticated": false', result.text)
        self.assertIn(CONSOLE_ORIGIN, result.text)

    def test_silent_sso_success_sets_business_cookie(self):
        response = self.client.get('/api/auth/oidc/login?app=weight&silent=1', base_url=API_ORIGIN)
        query = parse_qs(urlsplit(response.location).query)
        result, _ = self.callback(query['state'][0], self.claims(query['nonce'][0]))
        self.assertEqual(result.status_code, 200)
        self.assertIn('"authenticated": true', result.text)
        self.assertIn(WEIGHT_ORIGIN, result.text)
        self.assertTrue(any('access_token_cookie=' in c for c in result.headers.getlist('Set-Cookie')))

    def test_central_enforcement_rejects_legacy_cookie_session(self):
        state, nonce, _ = self.begin()
        self.callback(state, self.claims(nonce))
        self.app.config['OIDC_SESSION_ENFORCED'] = True
        result = self.client.get('/api/user/login/info', base_url=API_ORIGIN)
        self.assertEqual(result.json['code'], 5005)

    def test_central_outage_is_503_not_logout(self):
        from utils.central_session import encrypt_refresh_token
        state, nonce, _ = self.begin()
        self.callback(state, self.claims(nonce))
        session = AuthSession.query.first()
        session.oidc_refresh_token = encrypt_refresh_token('test-rt')
        session.oidc_checked_at = utc_now() - timedelta(minutes=5)
        db.session.commit()
        self.app.config['OIDC_SESSION_ENFORCED'] = True
        with patch('utils.central_session.requests.post', side_effect=TimeoutError):
            result = self.client.get('/api/user/login/info', base_url=API_ORIGIN)
        self.assertEqual(result.status_code, 503)
        self.assertIsNone(AuthSession.query.first().revoked_at)

    def test_expired_central_session_revokes_business_session(self):
        from utils.central_session import encrypt_refresh_token
        state, nonce, _ = self.begin()
        self.callback(state, self.claims(nonce))
        session = AuthSession.query.first()
        session.oidc_refresh_token = encrypt_refresh_token('test-rt')
        session.oidc_checked_at = utc_now() - timedelta(minutes=5)
        db.session.commit()
        self.app.config['OIDC_SESSION_ENFORCED'] = True
        response = Mock(status_code=400)
        response.json.return_value = {'error': 'invalid_grant'}
        with patch('utils.central_session.requests.post', return_value=response):
            result = self.client.get('/api/user/login/info', base_url=API_ORIGIN)
        self.assertEqual(result.json['code'], 5005)
        self.assertIsNotNone(AuthSession.query.first().revoked_at)

    def claims(self, expected_nonce, **changes):
        now = utc_now()
        result = {
            'sub': 'identity-tangtao',
            'sid': 'browser-a',
            'iss': self.app.config['OIDC_ISSUER'],
            'aud': 'server-console',
            'iat': int(now.timestamp()),
            'exp': int((now + timedelta(minutes=5)).timestamp()),
            'nonce': expected_nonce,
            'realm_access': {'roles': ['app-console', 'app-weight']},
        }
        result.update(changes)
        return result

    def callback(self, state, claims, signing_key=None):
        token = pyjwt.encode(claims, signing_key or self.private_key, algorithm='RS256')
        token_response = Mock()
        token_response.json.return_value = {'id_token': token}
        with patch.object(auth_api.requests, 'post', return_value=token_response) as exchange, \
                patch.object(auth_api.pyjwt, 'PyJWKClient') as jwks:
            jwks.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(
                key=self.private_key.public_key(),
            )
            response = self.client.get(CALLBACK_PATH, base_url=API_ORIGIN,
                                       query_string={'state': state, 'code': 'test-code'})
        return response, exchange

    def cookie_value(self, name, path='/'):
        cookie = self.client.get_cookie(name, domain='tt829.cn', path=path)
        self.assertIsNotNone(cookie)
        return cookie.value

    def test_proxy_login_canonicalizes_before_attempt_and_host_only_state(self):
        for origin in (CONSOLE_ORIGIN, WEIGHT_ORIGIN):
            response = self.client.get('/api/auth/oidc/login?app=weight', base_url=origin)
            self.assertEqual(response.location, API_ORIGIN + '/api/auth/oidc/login?app=weight')
            self.assertEqual(OidcLoginAttempt.query.count(), 0)
            self.assertFalse(response.headers.getlist('Set-Cookie'))
        state, _, response = self.begin()
        cookie = self.client.get_cookie(auth_api.OIDC_STATE_COOKIE,
                                        domain='api.tt829.cn', path=CALLBACK_PATH)
        self.assertEqual(cookie.value, state)
        self.assertTrue(cookie.origin_only)
        self.assertTrue(cookie.http_only)
        self.assertTrue(cookie.secure)
        self.assertEqual(cookie.same_site, 'Lax')
        self.assertEqual(cookie.max_age, 600)

    def test_reverse_proxy_http_scheme_does_not_cause_redirect_loop(self):
        response = self.client.get('/api/auth/oidc/login', base_url='http://api.tt829.cn')
        self.assertTrue(response.location.startswith(self.app.config['OIDC_ISSUER']))
        self.assertEqual(OidcLoginAttempt.query.count(), 1)

    def test_missing_and_mismatched_browser_state_reject_before_exchange(self):
        for cookie_state in (None, 'wrong-browser-state'):
            state, nonce, _ = self.begin()
            self.client.delete_cookie(auth_api.OIDC_STATE_COOKIE,
                                      domain='api.tt829.cn', path=CALLBACK_PATH)
            if cookie_state:
                self.client.set_cookie(auth_api.OIDC_STATE_COOKIE, cookie_state,
                                       domain='api.tt829.cn', path=CALLBACK_PATH)
            response, exchange = self.callback(state, self.claims(nonce))
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json['message'], 'Invalid login state')
            exchange.assert_not_called()
            self.assertEqual(AuthSession.query.count(), 0)

    def test_expired_attempt_rejects_before_exchange(self):
        state, nonce, _ = self.begin()
        OidcLoginAttempt.query.one().expires_at = utc_now() - timedelta(seconds=1)
        db.session.commit()
        response, exchange = self.callback(state, self.claims(nonce))
        self.assertEqual(response.status_code, 400)
        exchange.assert_not_called()
        self.assertEqual(AuthSession.query.count(), 0)

    def test_missing_roles_denies_instead_of_creating_session(self):
        state, nonce, _ = self.begin()
        claims = self.claims(nonce)
        del claims['realm_access']
        response, exchange = self.callback(state, claims)
        exchange.assert_called_once()
        self.assertEqual(response.location, CONSOLE_ORIGIN + '/login?auth_error=forbidden')
        self.assertEqual(AuthSession.query.count(), 0)
        self.assertEqual(OidcLoginAttempt.query.count(), 0)

    def test_app_role_and_identity_mapping_are_enforced(self):
        for app, changes, destination in (
            ('console', {'realm_access': {'roles': ['app-weight']}}, '/login?auth_error=forbidden'),
            ('console', {'sub': 'unmapped-identity'}, '/login?auth_error=unmapped'),
            ('weight', {'realm_access': {'roles': ['app-console']}}, '/?auth_error=forbidden'),
        ):
            with self.subTest(app=app, changes=changes):
                state, nonce, _ = self.begin(app)
                response, _ = self.callback(state, self.claims(nonce, **changes))
                origin = CONSOLE_ORIGIN if app == 'console' else WEIGHT_ORIGIN
                self.assertEqual(response.location, origin + destination)
                self.assertEqual(AuthSession.query.count(), 0)

    def test_nonce_subject_expiry_audience_issuer_and_signature_are_verified(self):
        for changes, key in (
            ({'nonce': 'wrong-nonce'}, None),
            ({'sub': None}, None),
            ({'exp': 1}, None),
            ({'aud': 'other-client'}, None),
            ({'iss': 'https://wrong-issuer.example'}, None),
            ({}, self.other_key),
        ):
            with self.subTest(changes=changes, wrong_key=key is not None):
                state, nonce, _ = self.begin()
                response, _ = self.callback(state, self.claims(nonce, **changes), key)
                self.assertEqual(response.location, CONSOLE_ORIGIN + '/login?auth_error=failed')
                self.assertEqual(AuthSession.query.count(), 0)
                self.assertEqual(OidcLoginAttempt.query.count(), 0)

    def test_success_cleans_old_cookies_and_supports_get_post_refresh_logout(self):
        # Prior deployments wrote both host-only and domain cookies at two paths.
        for domain in ('api.tt829.cn', 'tt829.cn'):
            for name in auth_api.AUTH_COOKIE_NAMES:
                for path in ('/', '/api/auth'):
                    self.client.set_cookie(name, 'stale', domain=domain, path=path,
                                           origin_only=domain == 'api.tt829.cn')
        state, nonce, _ = self.begin()
        response, exchange = self.callback(state, self.claims(nonce))
        self.assertEqual(response.location, CONSOLE_ORIGIN)
        self.assertEqual(AuthSession.query.count(), 1)
        self.assertEqual(OidcLoginAttempt.query.count(), 0)
        self.assertEqual(exchange.call_args.kwargs['data']['redirect_uri'], API_ORIGIN + CALLBACK_PATH)
        self.assertTrue(exchange.call_args.kwargs['data']['code_verifier'])
        access = self.client.get_cookie('access_token_cookie', domain='tt829.cn')
        csrf_access = self.client.get_cookie('csrf_access_token', domain='tt829.cn')
        self.assertFalse(access.origin_only)
        self.assertTrue(access.http_only)
        self.assertTrue(access.secure)
        self.assertFalse(csrf_access.http_only)
        self.assertEqual(decode_token(access.value)['sub'], 'tangtao')
        for name in auth_api.AUTH_COOKIE_NAMES:
            for path in ('/', '/api/auth'):
                self.assertIsNone(self.client.get_cookie(name, domain='api.tt829.cn', path=path))
        self.assertIsNone(self.client.get_cookie('refresh_token_cookie', domain='tt829.cn'))
        self.assertIsNone(self.client.get_cookie(auth_api.OIDC_STATE_COOKIE,
                                                 domain='api.tt829.cn', path=CALLBACK_PATH))

        for origin in (CONSOLE_ORIGIN, WEIGHT_ORIGIN):
            info = self.client.get('/api/user/login/info', base_url=API_ORIGIN,
                                   headers={'Origin': origin})
            self.assertEqual(info.json['data']['username'], 'tangtao')
            self.assertEqual(info.headers['Access-Control-Allow-Origin'], origin)
            self.assertEqual(info.headers['Access-Control-Allow-Credentials'], 'true')
            denied = self.client.post('/api/user/profile/update', base_url=API_ORIGIN,
                                      headers={'Origin': origin}, json={'displayName': 'not applied'})
            self.assertEqual(denied.json['code'], 5003)
            updated = self.client.post('/api/user/profile/update', base_url=API_ORIGIN,
                                       headers={'Origin': origin, 'X-CSRF-TOKEN': csrf_access.value},
                                       json={'displayName': 'updated'})
            self.assertEqual(updated.json['code'], 200)

        session = AuthSession.query.one()
        old_jti = session.current_refresh_jti
        refresh = self.client.post('/api/auth/token/refresh', base_url=API_ORIGIN,
                                   headers={'Origin': WEIGHT_ORIGIN,
                                            'X-CSRF-TOKEN': self.cookie_value('csrf_refresh_token')})
        self.assertEqual(refresh.json['code'], 200)
        self.assertNotEqual(session.current_refresh_jti, old_jti)
        self.assertEqual(session.previous_refresh_jti, old_jti)
        access_token = self.cookie_value('access_token_cookie')
        logout = self.client.post('/api/auth/logout', base_url=API_ORIGIN,
                                  headers={'Origin': CONSOLE_ORIGIN,
                                           'X-CSRF-TOKEN': self.cookie_value('csrf_refresh_token')})
        self.assertEqual(logout.json['code'], 200)
        self.assertIsNotNone(session.revoked_at)
        self.assertIsNone(self.client.get_cookie('access_token_cookie', domain='tt829.cn'))
        self.client.set_cookie('access_token_cookie', access_token, domain='tt829.cn', origin_only=False)
        info = self.client.get('/api/user/login/info', base_url=API_ORIGIN)
        self.assertEqual(info.json['code'], 5005)

        # Even restoring an old browser state cannot reuse a consumed attempt.
        self.client.set_cookie(auth_api.OIDC_STATE_COOKIE, state,
                               domain='api.tt829.cn', path=CALLBACK_PATH)
        replay, repeated_exchange = self.callback(state, self.claims(nonce))
        self.assertEqual(replay.status_code, 400)
        repeated_exchange.assert_not_called()
        self.assertEqual(AuthSession.query.count(), 1)

    def test_legacy_password_login_also_replaces_host_only_cookie_variants(self):
        self.client.set_cookie('access_token_cookie', 'stale', domain='api.tt829.cn')
        self.client.set_cookie('refresh_token_cookie', 'stale', domain='api.tt829.cn', path='/api/auth')
        response = self.client.post('/api/auth/login', base_url=API_ORIGIN,
                                    json={'username': 'tangtao', 'password': 'test-password'})
        self.assertEqual(response.json['code'], 200)
        self.assertIsNone(self.client.get_cookie('access_token_cookie', domain='api.tt829.cn'))
        self.assertIsNone(self.client.get_cookie('refresh_token_cookie', domain='api.tt829.cn', path='/api/auth'))
        self.assertEqual(decode_token(self.cookie_value('access_token_cookie'))['sub'], 'tangtao')

    def test_backchannel_logout_is_verified_and_scoped_to_one_browser(self):
        state, nonce, _ = self.begin()
        self.callback(state, self.claims(nonce))
        state, nonce, _ = self.begin()
        self.callback(state, self.claims(nonce, sid='browser-b'))
        claims = self.claims(nonce)
        del claims['nonce']
        claims.update(jti='logout-1', events={'http://schemas.openid.net/event/backchannel-logout': {}})
        with patch.object(auth_api.pyjwt, 'PyJWKClient') as jwks:
            jwks.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.private_key.public_key())
            for changes, key in (({'nonce': nonce}, self.private_key), ({'aud': 'other'}, self.private_key),
                                 ({'events': {}}, self.private_key), ({'sid': ''}, self.private_key),
                                 ({'exp': 1}, self.private_key), ({}, self.other_key)):
                token = pyjwt.encode({**claims, **changes}, key, algorithm='RS256')
                response = self.client.post('/api/auth/oidc/backchannel-logout', base_url=API_ORIGIN,
                                            data={'logout_token': token})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(AuthSession.query.filter(AuthSession.revoked_at.is_(None)).count(), 2)
            token = pyjwt.encode(claims, self.private_key, algorithm='RS256')
            for _ in range(2):
                response = self.client.post('/api/auth/oidc/backchannel-logout', base_url=API_ORIGIN,
                                            data={'logout_token': token})
                self.assertEqual(response.status_code, 200)
                self.assertIsNotNone(AuthSession.query.filter_by(oidc_sid='browser-a').one().revoked_at)
                self.assertIsNone(AuthSession.query.filter_by(oidc_sid='browser-b').one().revoked_at)

    def test_unified_logout_requires_csrf_and_returns_provider_url(self):
        state, nonce, _ = self.begin()
        self.callback(state, self.claims(nonce))
        path = '/api/auth/logout?unified=1&app=console'
        self.assertEqual(self.client.post(path, base_url=API_ORIGIN).status_code, 401)
        self.assertIsNone(AuthSession.query.one().revoked_at)
        response = self.client.post(path, base_url=API_ORIGIN,
                                    headers={'X-CSRF-TOKEN': self.cookie_value('csrf_refresh_token')})
        self.assertEqual(response.status_code, 200)
        location = urlsplit(response.json['data']['logoutUrl'])
        self.assertEqual(location.netloc, 'auth.example')
        self.assertEqual(parse_qs(location.query)['post_logout_redirect_uri'], [CONSOLE_ORIGIN + '/login'])
        self.assertIsNotNone(AuthSession.query.one().revoked_at)


if __name__ == '__main__':
    unittest.main()
