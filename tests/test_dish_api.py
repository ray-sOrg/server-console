"""Offline tests only: isolated SQLite, never the configured restaurant DB."""
import unittest
from unittest.mock import patch

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from extensions import db
from model.user import User
from model.dish import Dish, DishNutrition, RestaurantBase
from utils.dish_validation import dish_payload, nutrition_payload

with patch.object(config, 'DATABASE_RESTAURANT', 'sqlite://'):
    from api import dish_api


def nutrition(**overrides):
    return dict({
        'basis': 'PER_100G', 'servingUnit': 'g', 'defaultServingAmount': 100,
        'caloriesKcal': 97.28, 'proteinG': 15.4, 'fatG': 1.2,
        'carbohydrateG': 5.9, 'sugarG': 0, 'sodiumMg': 417,
    }, **overrides)


class DishApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        RestaurantBase.metadata.create_all(self.engine)
        self.session = sessionmaker(bind=self.engine)
        self.session_patch = patch.object(dish_api, 'RestaurantSession', self.session)
        self.session_patch.start()
        app = Flask(__name__)
        app.config.update(
            SQLALCHEMY_DATABASE_URI='sqlite://',
            JWT_SECRET_KEY='offline-test-key-at-least-32-characters',
            JWT_TOKEN_LOCATION=['headers'],
        )
        db.init_app(app)
        JWTManager(app)
        self.context = app.app_context()
        self.context.push()
        User.__table__.create(db.engine)
        db.session.add(User(username='dish-admin', password='unused', role='admin'))
        db.session.commit()
        app.register_blueprint(dish_api.dish_api_pb, url_prefix='/api/chuan-dai')
        self.client = app.test_client()
        self.client.environ_base['HTTP_AUTHORIZATION'] = (
            'Bearer ' + create_access_token(identity='dish-admin')
        )

    def tearDown(self):
        self.session_patch.stop()
        db.session.remove()
        db.engine.dispose()
        self.context.pop()
        self.engine.dispose()

    def create(self, **overrides):
        data = dict({'name': '原味鸡排', 'category': 'FITNESS_MEAL', 'nutrition': nutrition()}, **overrides)
        return self.client.post('/api/chuan-dai/dish', json=data).get_json()

    def test_create_read_update_preserve_zero_and_null(self):
        created = self.create()
        self.assertEqual(created['code'], 200)
        dish = created['data']
        self.assertEqual(dish['price'], 0)
        self.assertEqual(dish['nutrition']['sugarG'], 0)
        self.assertIsNone(dish['nutrition']['fiberG'])
        self.assertEqual(dish['nutrition']['caloriesKcal'], 97.28)
        url = '/api/chuan-dai/dish/' + dish['id']
        self.assertEqual(self.client.get(url).get_json()['data'], dish)
        updated = self.client.put(url, json={'nutrition': nutrition(fatG=1.4)}).get_json()
        self.assertEqual(updated['data']['nutrition']['fatG'], 1.4)
        renamed = self.client.put(url, json={'name': '鸡排'}).get_json()
        self.assertEqual(renamed['data']['nutrition']['fatG'], 1.4)
        self.assertEqual(self.client.get('/api/chuan-dai/dish/list').get_json()['data'][0]['nutrition']['fatG'], 1.4)

    def test_ordinary_dish_keeps_existing_nutrition_on_category_change(self):
        dish = self.create()['data']
        url = '/api/chuan-dai/dish/' + dish['id']
        changed = self.client.put(url, json={'category': 'OTHER'}).get_json()
        self.assertIsNotNone(changed['data']['nutrition'])
        cleared = self.client.put(url, json={'nutrition': None}).get_json()
        self.assertIsNone(cleared['data']['nutrition'])
        ordinary = self.create(name='汤', category='SOUP', nutrition=None)
        self.assertEqual(ordinary['code'], 200)

    def test_invalid_update_is_atomic_and_fitness_requires_nutrition(self):
        dish = self.create()['data']
        url = '/api/chuan-dai/dish/' + dish['id']
        failed = self.client.put(url, json={'name': '不应保存', 'nutrition': nutrition(proteinG=-1)}).get_json()
        self.assertEqual(failed['code'], 400)
        self.assertEqual(self.client.get(url).get_json()['data']['name'], dish['name'])
        self.assertEqual(self.client.put(url, json={'nutrition': None}).get_json()['code'], 400)
        self.assertEqual(self.create(nutrition=None)['code'], 400)

    def test_toggle_and_delete(self):
        dish = self.create()['data']
        url = '/api/chuan-dai/dish/' + dish['id']
        toggled = self.client.post(url + '/toggle').get_json()
        self.assertFalse(toggled['data']['isAvailable'])
        self.assertEqual(self.client.delete(url).get_json()['code'], 200)
        with self.session() as session:
            self.assertEqual(session.query(DishNutrition).count(), 0)
            self.assertEqual(session.query(Dish).count(), 0)

    def test_validation(self):
        for values in (
            {'servingUnit': 'piece'}, {'defaultServingAmount': 0},
            {'caloriesKcal': 'NaN'}, {'proteinG': 'Infinity'},
            {'proteinG': True}, {'caloriesKcal': None}, {'fatG': 0.001},
            {'labelImageUrl': 'javascript:alert(1)'},
        ):
            with self.subTest(values=values), self.assertRaises(ValueError):
                nutrition_payload(nutrition(**values))
        for basis, unit in [('PER_100G', 'g'), ('PER_100ML', 'ml'), ('PER_SERVING', 'piece'), ('PER_SERVING', 'serving')]:
            self.assertEqual(nutrition_payload(nutrition(basis=basis, servingUnit=unit))['servingUnit'], unit)
        self.assertEqual(dish_payload({'name': '汤', 'category': 'SOUP'})['price'], 0)


if __name__ == '__main__':
    unittest.main()
