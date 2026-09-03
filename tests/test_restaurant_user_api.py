"""Offline coverage of restaurant DB isolation, admin access and pagination."""
import unittest
from datetime import datetime
from hashlib import sha256
from unittest.mock import patch
from uuid import uuid4

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token, decode_token
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

import config
from extensions import db
from model.user import User
from model.restaurant_user import (
    RestaurantAuthRateLimit, RestaurantSession, RestaurantUser,
)

with patch.object(config, 'DATABASE_RESTAURANT', 'sqlite://'):
    from api import restaurant_user_api

OLD_PASSWORD_HASH = restaurant_user_api.password_hasher.hash('Previous123!')


class RestaurantUserApiTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            SQLALCHEMY_DATABASE_URI='sqlite://',
            JWT_SECRET_KEY='offline-test-key-at-least-32-characters',
            JWT_TOKEN_LOCATION=['headers'],
        )
        db.init_app(self.app)
        JWTManager(self.app)
        self.app.register_blueprint(
            restaurant_user_api.restaurant_user_api_pb,
            url_prefix='/api/chuan-dai',
        )
        self.context = self.app.app_context()
        self.context.push()
        User.__table__.create(db.engine)
        db.session.add_all([
            User(username='console-admin', password='unused', role='admin'),
            User(username='console-user', password='unused', role='user'),
        ])
        db.session.commit()
        self.engine = create_engine('sqlite://')
        RestaurantUser.__table__.create(self.engine)
        RestaurantSession.__table__.create(self.engine)
        RestaurantAuthRateLimit.__table__.create(self.engine)
        self.session = sessionmaker(bind=self.engine)
        self.session_patch = patch.object(
            restaurant_user_api, 'get_restaurant_session', self.session,
        )
        self.session_patch.start()
        self.ids = [str(uuid4()) for _ in range(12)]
        with self.session.begin() as session:
            session.add_all([
                RestaurantUser(
                    id=self.ids[i], account=f'guest{i:02}',
                    passwordHash=OLD_PASSWORD_HASH,
                    nickname='小川_100%' if i == 0 else None,
                    phone='13800000000' if i == 0 else None,
                    role='HOST' if i == 0 else 'GUEST',
                    createdAt=datetime(2026, 9, 1, 0, i),
                ) for i in range(12)
            ])
            session.add_all([
                RestaurantSession(id='target-session-1', userId=self.ids[0], expiresAt=datetime(2027, 1, 1)),
                RestaurantSession(id='target-session-2', userId=self.ids[0], expiresAt=datetime(2027, 1, 1)),
                RestaurantSession(id='other-session', userId=self.ids[1], expiresAt=datetime(2027, 1, 1)),
            ])
            session.add_all([
                RestaurantAuthRateLimit(key=sha256(value.encode()).hexdigest())
                for value in ('account:guest00', 'account:guest01', 'ip:127.0.0.1')
            ])
        self.client = self.app.test_client()
        self.headers = self.auth('console-admin')

    def tearDown(self):
        self.session_patch.stop()
        db.session.remove()
        db.engine.dispose()
        self.context.pop()
        self.engine.dispose()

    def auth(self, identity):
        return {'Authorization': f'Bearer {create_access_token(identity=identity)}'}

    def get(self, query=''):
        return self.client.get(
            '/api/chuan-dai/user/list' + query, headers=self.headers,
        ).get_json()

    def test_pagination_and_database_isolation(self):
        first = self.get()['data']
        self.assertEqual(first['total'], 12)
        self.assertEqual(len(first['items']), 10)
        self.assertEqual(first['items'][0]['account'], 'guest11')
        second = self.get('?pageNumber=2')['data']
        self.assertEqual(len(second['items']), 2)
        self.assertFalse({u['id'] for u in first['items']} & {u['id'] for u in second['items']})
        self.assertEqual(self.get('?pageNumber=999')['data']['pageNumber'], 2)
        self.assertNotIn('User', db.metadata.tables)

    def test_search_role_and_literal_wildcards(self):
        for query in ('?keyword=GUEST00', '?keyword=小川', '?keyword=1380000',
                      '?keyword=%25', '?keyword=_', '?role=HOST'):
            with self.subTest(query=query):
                result = self.get(query)['data']
                self.assertEqual(result['total'], 1)
                self.assertEqual(result['items'][0]['id'], self.ids[0])
        self.assertEqual(self.get('?keyword=小川&role=GUEST')['data']['total'], 0)

    def test_empty_result(self):
        result = self.get('?keyword=missing&pageNumber=99')['data']
        self.assertEqual(result['items'], [])
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['pageNumber'], 1)

    def test_invalid_parameters(self):
        for query in ('?pageNumber=0', '?pageNumber=abc', '?pageSize=-1',
                      '?pageSize=101', '?role=ADMIN', '?keyword=' + 'x' * 101):
            with self.subTest(query=query):
                self.assertEqual(self.get(query)['code'], 400)

    def test_detail_allowlist_nulls_and_utc(self):
        result = self.client.get(
            '/api/chuan-dai/user/' + self.ids[0], headers=self.headers,
        ).get_json()
        self.assertEqual(result['code'], 200)
        self.assertEqual(set(result['data']), {
            'id', 'account', 'nickname', 'avatar', 'phone', 'gender',
            'birthday', 'bio', 'role', 'createdAt', 'updatedAt', 'lastLoginAt',
        })
        self.assertIsNone(result['data']['lastLoginAt'])
        self.assertTrue(result['data']['createdAt'].endswith('+00:00'))

    def test_unknown_and_invalid_id(self):
        for user_id, code in ((str(uuid4()), 404), ('invalid', 400)):
            result = self.client.get(
                '/api/chuan-dai/user/' + user_id, headers=self.headers,
            ).get_json()
            self.assertEqual(result['code'], code)

    def test_admin_only_and_missing_login(self):
        for path in ('/api/chuan-dai/user/list', '/api/chuan-dai/user/' + self.ids[0]):
            self.assertEqual(self.client.get(path).status_code, 401)
            for identity in ('console-user', 'deleted-admin'):
                result = self.client.get(path, headers=self.auth(identity)).get_json()
                self.assertEqual(result['code'], 403)

    def test_database_failure_is_not_empty_list(self):
        with patch.object(restaurant_user_api, 'get_restaurant_session', side_effect=RuntimeError('private DSN')):
            result = self.get()
        self.assertEqual(result['code'], 500)
        self.assertIsNone(result['data'])
        self.assertNotIn('private DSN', str(result))

    def reset(self, user_id=None, values=None, headers=None):
        return self.client.post(
            '/api/chuan-dai/user/' + (user_id or self.ids[0]) + '/reset-password',
            json=values if values is not None else {
                'newPassword': 'NewPassword123!', 'confirmPassword': 'NewPassword123!',
            },
            headers=self.headers if headers is None else headers,
        )

    def stored_hash(self, user_id):
        with self.session() as session:
            return session.scalar(select(RestaurantUser.passwordHash).where(RestaurantUser.id == user_id))

    def test_reset_hashes_password_and_revokes_only_target_sessions(self):
        result = self.reset().get_json()
        self.assertEqual(result['code'], 200)
        self.assertEqual(result['data'], {'id': self.ids[0]})
        password_hash = self.stored_hash(self.ids[0])
        self.assertNotEqual(password_hash, OLD_PASSWORD_HASH)
        self.assertTrue(password_hash.startswith('$argon2id$'))
        self.assertTrue(restaurant_user_api.password_hasher.verify(password_hash, 'NewPassword123!'))
        self.assertEqual(self.stored_hash(self.ids[1]), OLD_PASSWORD_HASH)
        with self.session() as session:
            self.assertEqual([s.id for s in session.query(RestaurantSession).all()], ['other-session'])
            self.assertIsNotNone(session.get(RestaurantUser, self.ids[0]).updatedAt)
            self.assertIsNone(session.get(RestaurantAuthRateLimit, sha256(b'account:guest00').hexdigest()))
            self.assertEqual(session.query(RestaurantAuthRateLimit).count(), 2)
        # Password hashes stay out of both profile queries and API responses.
        with self.session() as session:
            user = session.get(RestaurantUser, self.ids[0])
            self.assertNotIn('passwordHash', user.__dict__)
        self.assertNotIn('passwordHash', str(self.get()))

    def test_reset_rejects_invalid_passwords_without_changes(self):
        invalid = [None, 123456, 'abc12', '12345678', 'abcdefgh', 'A1' * 33,
                   'abc１２３', 'Ab1' + '\U0001f600' * 31, '\ud800Abc123']
        for password in invalid:
            with self.subTest(password=password):
                result = self.reset(values={'newPassword': password, 'confirmPassword': password}).get_json()
                self.assertEqual(result['code'], 400)
        for values in ({}, [], {'newPassword': 'Abc123'},
                       {'newPassword': 'Abc123', 'confirmPassword': 'different123'}):
            self.assertEqual(self.reset(values=values).get_json()['code'], 400)
        self.assertEqual(self.stored_hash(self.ids[0]), OLD_PASSWORD_HASH)
        with self.session() as session:
            self.assertEqual(session.query(RestaurantSession).count(), 3)

    def test_reset_requires_admin_and_valid_target(self):
        self.assertEqual(self.reset(headers={}).status_code, 401)
        for identity in ('console-user', 'deleted-admin'):
            self.assertEqual(self.reset(headers=self.auth(identity)).get_json()['code'], 403)
        self.assertEqual(self.reset(user_id='invalid').get_json()['code'], 400)
        self.assertEqual(self.reset(user_id=str(uuid4())).get_json()['code'], 404)
        self.assertEqual(self.stored_hash(self.ids[0]), OLD_PASSWORD_HASH)

    def test_cookie_reset_requires_matching_csrf_header(self):
        self.app.config['JWT_TOKEN_LOCATION'] = ['cookies']
        token = create_access_token(identity='console-admin')
        self.client.set_cookie('access_token_cookie', token)
        self.assertEqual(self.reset(headers={}).status_code, 401)
        self.assertEqual(self.reset(headers={'X-CSRF-TOKEN': 'incorrect'}).status_code, 401)
        result = self.reset(headers={'X-CSRF-TOKEN': decode_token(token)['csrf']})
        self.assertEqual(result.get_json()['code'], 200)

    def test_session_deletion_failure_rolls_back_password(self):
        with self.engine.begin() as connection:
            connection.execute(text(
                'CREATE TRIGGER fail_session_delete BEFORE DELETE ON "Session" '
                "BEGIN SELECT RAISE(ABORT, 'injected failure'); END;"
            ))
        with self.assertLogs(self.app.logger, level='ERROR') as logs:
            result = self.reset().get_json()
        self.assertEqual(result['code'], 500)
        self.assertNotIn('NewPassword123!', str(result) + str(logs.output))
        self.assertNotIn('$argon2', str(logs.output))
        self.assertEqual(self.stored_hash(self.ids[0]), OLD_PASSWORD_HASH)
        with self.session() as session:
            self.assertEqual(session.query(RestaurantSession).count(), 3)
            self.assertEqual(session.query(RestaurantAuthRateLimit).count(), 3)


if __name__ == '__main__':
    unittest.main()
