"""Real JWT/session checks against isolated SQLite; no production app import."""
import unittest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import bcrypt
from flask import Flask
from flask_jwt_extended import create_access_token

import config
from extensions import db, jwt
from model.auth_session import AuthSession
from model.oidc_login_attempt import OidcLoginAttempt
from model.user import User
from model.wedding_music import WeddingMusic
from model.wedding_photo_wall import WeddingPhotoWall
from model.tracked_person import TrackedPerson
from model.weight_record import WeightRecord
from utils.auth_session_utils import utc_now
from utils.jwt_errors import register_jwt_errors
from api import auth_api, user_api, wedding_api, test_api, oss_api, image_api, upload_api, weight_api

with patch.object(config, 'DATABASE_RESTAURANT', 'sqlite://'):
    from api import dish_api


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            JWT_SECRET_KEY='offline-test-key-at-least-32-characters',
            JWT_TOKEN_LOCATION=['headers'],
            OIDC_ISSUER='https://auth.example/realms/test',
            OIDC_CLIENT_ID='server-console',
            OIDC_CLIENT_SECRET='test-secret',
            OIDC_CALLBACK_URL='https://api.example/api/auth/oidc/callback',
        )
        db.init_app(self.app)
        jwt.init_app(self.app)
        register_jwt_errors()
        for blueprint, prefix in (
            (user_api.user_api_pb, '/api'),
            (wedding_api.wedding_api_pb, '/api'),
            (test_api.test_api_pb, '/api'),
            (oss_api.oss_api_pb, '/api'),
            (image_api.image_api_pb, '/api'),
            (upload_api.upload_api_pb, '/api'),
            (weight_api.weight_api_pb, '/api'),
            (auth_api.auth_api_pb, '/api'),
            (dish_api.dish_api_pb, '/api/chuan-dai'),
        ):
            self.app.register_blueprint(blueprint, url_prefix=prefix)
        self.context = self.app.app_context()
        self.context.push()
        for model in (User, AuthSession, OidcLoginAttempt, WeddingMusic, WeddingPhotoWall,
                      TrackedPerson, WeightRecord):
            model.__table__.create(db.engine)
        for name, role in (
            ('root', 'super_admin'), ('admin', 'admin'),
            ('member', 'user'), ('other', 'user'),
        ):
            db.session.add(User(username=name, password='unused', role=role))
        db.session.commit()
        self.client = self.app.test_client()
        self.slowdown = patch.object(user_api.time, 'sleep')
        self.slowdown.start()

    def tearDown(self):
        self.slowdown.stop()
        db.session.remove()
        db.engine.dispose()
        self.context.pop()

    def auth(self, name, revoked=False, expired_session=False):
        session = AuthSession(
            user_identity=name,
            expires_at=utc_now() + timedelta(days=-1 if expired_session else 1),
            revoked_at=utc_now() if revoked else None,
        )
        db.session.add(session)
        db.session.commit()
        token = create_access_token(
            identity=name,
            additional_claims={'sid': session.session_id, 'role': 'super_admin'},
        )
        return {'Authorization': 'Bearer ' + token}

    def request(self, method, path, headers=None, data=None):
        return self.client.open(path, method=method, headers=headers, json=data)

    def test_all_management_routes_reject_anonymous_members_and_deleted_users(self):
        routes = [
            ('GET', '/api/user/list'), ('POST', '/api/user/add'),
            ('POST', '/api/user/delete'),
            ('POST', '/api/chuan-dai/dish'),
            ('PUT', '/api/chuan-dai/dish/unknown'),
            ('DELETE', '/api/chuan-dai/dish/unknown'),
            ('POST', '/api/chuan-dai/dish/unknown/toggle'),
            ('POST', '/api/wedding/music/add'),
            ('POST', '/api/wedding/photo/wall/add'),
            ('POST', '/api/wedding/photo/wall/edit'),
            ('POST', '/api/wedding/photo/wall/delete'),
            ('GET', '/api/test/db'), ('GET', '/api/test/flask_env'),
            ('GET', '/api/test/celery'),
            ('GET', '/api/oss/credentials?type=image'),
            ('GET', '/api/oss/images/list'),
            ('GET', '/api/image/asyncOss'),
            ('GET', '/api/image/task_status/unknown'),
            ('POST', '/api/upload/images'),
        ]
        member_headers = self.auth('member')
        deleted_headers = self.auth('other')
        db.session.delete(User.query.filter_by(username='other').one())
        db.session.commit()
        with patch.object(dish_api, 'get_restaurant_session') as restaurant:
            for method, path in routes:
                for headers, code in ((None, 5003), (member_headers, 403),
                                      (deleted_headers, 403)):
                    with self.subTest(path=path, code=code):
                        result = self.request(method, path, headers, {}).get_json()
                        self.assertEqual(result['code'], code)
            restaurant.assert_not_called()
        self.assertEqual(User.query.count(), 3)
        self.assertEqual(WeddingMusic.query.count(), 0)
        self.assertEqual(WeddingPhotoWall.query.count(), 0)

    def test_admin_creation_hierarchy_and_password_hash(self):
        for actor, target_role, code in (
            ('admin', 'admin', 403), ('admin', 'super_admin', 403),
            ('admin', 'user', 200), ('root', 'admin', 200),
            ('root', 'super_admin', 200),
        ):
            with self.subTest(actor=actor, role=target_role):
                name = actor + '-' + target_role
                result = self.request('POST', '/api/user/add', self.auth(actor), {
                    'username': name, 'password': 'NewPassword123!', 'role': target_role,
                }).get_json()
                self.assertEqual(result['code'], code)
                user = User.query.filter_by(username=name).first()
                if code == 403:
                    self.assertIsNone(user)
                else:
                    self.assertTrue(bcrypt.checkpw(b'NewPassword123!', user.password.encode()))

    def test_delete_hierarchy_and_self_protection(self):
        for actor, target, code in (
            ('admin', 'root', 403), ('admin', 'admin', 403),
            ('root', 'root', 403), ('admin', 'other', 200),
            ('root', 'admin', 200),
        ):
            with self.subTest(actor=actor, target=target):
                uid = User.query.filter_by(username=target).one().uid
                result = self.request('POST', '/api/user/delete', self.auth(actor), {
                    'uuid': uid,
                }).get_json()
                self.assertEqual(result['code'], code)
                self.assertEqual(User.query.filter_by(uid=uid).count(), int(code != 200))

    def test_current_db_role_overrides_old_privileged_token(self):
        headers = self.auth('admin')
        User.query.filter_by(username='admin').one().role = 'user'
        db.session.commit()
        result = self.request('GET', '/api/user/list', headers).get_json()
        self.assertEqual(result['code'], 403)

    def test_revoked_expired_session_and_expired_token_are_denied(self):
        for options in ({'revoked': True}, {'expired_session': True}):
            result = self.request('GET', '/api/user/list', self.auth('admin', **options))
            self.assertEqual(result.get_json()['code'], 5005)
        token = create_access_token(identity='admin', expires_delta=timedelta(seconds=-1))
        result = self.request('GET', '/api/user/list', {'Authorization': 'Bearer ' + token})
        self.assertEqual(result.get_json()['code'], 5001)

    def test_member_self_service_and_admin_list_still_work(self):
        headers = self.auth('member')
        result = self.request('GET', '/api/user/login/info', headers).get_json()
        self.assertEqual(result['data']['username'], 'member')
        result = self.request('POST', '/api/user/profile/update', headers, {
            'displayName': '我的名字', 'role': 'super_admin', 'username': 'root',
        }).get_json()
        self.assertEqual(result['code'], 200)
        self.assertEqual(User.query.filter_by(username='member').one().role, 'user')
        self.assertEqual(self.request('GET', '/api/user/list', self.auth('admin')).get_json()['code'], 200)

    def test_wedding_admin_write_and_public_reads(self):
        result = self.request('POST', '/api/wedding/music/add', self.auth('admin'), {
            'title': 'Test', 'artist': 'Test Artist',
            'url': 'https://example.invalid/test.mp3',
        }).get_json()
        self.assertEqual(result['code'], 200)
        for path in ('/api/wedding/music/list', '/api/wedding/photo/wall/list',
                     '/api/wedding/photo/wall/list/all'):
            self.assertEqual(self.request('GET', path).get_json()['code'], 200)

    def test_weight_records_remain_isolated_by_existing_identity(self):
        for name, weight in (('member', '60'), ('other', '80')):
            db.session.add(WeightRecord(
                user_identity=name, weight=Decimal(weight), record_date=date(2026, 9, 4),
            ))
        db.session.commit()
        headers = self.auth('member')
        result = self.request('GET', '/api/weight/records/all', headers).get_json()
        self.assertEqual(result['code'], 200)
        self.assertEqual([r['userIdentity'] for r in result['data']], ['member'])
        foreign_id = WeightRecord.query.filter_by(user_identity='other').one().id
        result = self.request('POST', '/api/weight/record/delete', headers, {
            'id': foreign_id,
        }).get_json()
        self.assertNotEqual(result['code'], 200)
        self.assertEqual(WeightRecord.query.count(), 2)

    def test_oidc_login_validates_target_and_persists_pkce_attempt(self):
        self.assertEqual(
            self.client.get('/api/auth/oidc/login?app=unknown').status_code, 400,
        )
        response = self.client.get('/api/auth/oidc/login?app=weight', base_url='https://api.example')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.startswith(
            'https://auth.example/realms/test/protocol/openid-connect/auth?',
        ))
        self.assertIn('code_challenge_method=S256', response.location)
        self.assertTrue(any('console_oidc_state_v3=' in value and 'Max-Age=600' in value
                            for value in response.headers.getlist('Set-Cookie')))
        attempt = OidcLoginAttempt.query.one()
        self.assertEqual(attempt.target_app, 'weight')
        self.assertNotIn(attempt.code_verifier, response.location)


if __name__ == '__main__':
    unittest.main()
