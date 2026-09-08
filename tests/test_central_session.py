import unittest
from unittest.mock import patch, Mock
from flask import Flask
from utils.central_session import encrypt_refresh_token, decrypt_refresh_token, central_session_active, CentralSessionUnavailable
from types import SimpleNamespace


class CentralSessionTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(OIDC_CLIENT_SECRET='test-secret', OIDC_CLIENT_ID='test-client', OIDC_ISSUER='https://auth.invalid', OIDC_SESSION_ENFORCED=True)
        self.context = app.app_context()
        self.context.push()

    def tearDown(self):
        self.context.pop()

    def test_refresh_credential_is_encrypted_and_authenticated(self):
        token = encrypt_refresh_token('private-token')
        self.assertNotIn('private-token', token)
        self.assertEqual(decrypt_refresh_token(token), 'private-token')
        with self.assertRaises(Exception):
            decrypt_refresh_token(token[:-4] + 'xxxx')

    def test_legacy_sessions_are_not_central_sessions(self):
        self.assertFalse(central_session_active(SimpleNamespace(oidc_sid=None)))
        self.assertFalse(central_session_active(SimpleNamespace(oidc_sid='old', oidc_refresh_token=None)))

    def test_outage_fails_closed_without_revoking_session(self):
        session = SimpleNamespace(oidc_sid='sid', oidc_refresh_token=encrypt_refresh_token('rt'), oidc_checked_at=None)
        with patch('utils.central_session.requests.post', side_effect=TimeoutError), patch('utils.central_session.AuthSession') as model:
            with self.assertRaises(CentralSessionUnavailable):
                central_session_active(session)
            model.query.filter_by.assert_not_called()
