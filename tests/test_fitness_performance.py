"""Regression checks for fitness database round trips and committed responses."""
import unittest
from datetime import date
from unittest.mock import patch

from flask import Flask
from sqlalchemy import event

from extensions import db
from api.fitness_api import commit_session_response
from model.fitness_session import FitnessSession
from utils.fitness_seed import ensure_default_fitness_data


class FitnessPerformanceTests(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config.update(SQLALCHEMY_DATABASE_URI='sqlite://', TESTING=True)
        db.init_app(app)
        self.context = app.app_context()
        self.context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_repeated_seed_does_not_commit_or_expire_loaded_plan(self):
        ensure_default_fitness_data(db, 'test-user')
        plan = ensure_default_fitness_data(db, 'test-user')
        with patch.object(db.session, 'commit', wraps=db.session.commit) as commit:
            again = ensure_default_fitness_data(db, 'test-user')
        self.assertEqual(plan.id, again.id)
        commit.assert_not_called()

    def test_seed_media_changes_are_still_committed(self):
        plan = ensure_default_fitness_data(db, 'test-user')
        exercise = plan.days[0].exercises[0].exercise
        exercise.media = None
        db.session.commit()
        with patch.object(db.session, 'commit', wraps=db.session.commit) as commit:
            ensure_default_fitness_data(db, 'test-user')
        commit.assert_called_once()

    def test_response_does_not_query_after_commit_and_changes_persist(self):
        session = FitnessSession(
            user_identity='test-user', subject_key='self',
            scheduled_date=date.today(), weekday=1, name='Workout',
            status='in_progress',
        )
        db.session.add(session)
        committed = []
        late_queries = []

        def after_commit(_session):
            committed.append(True)

        def before_execute(_conn, _cursor, statement, *_args):
            if committed:
                late_queries.append(statement)

        event.listen(db.session(), 'after_commit', after_commit)
        event.listen(db.engine, 'before_cursor_execute', before_execute)
        try:
            response, status = commit_session_response(session)
        finally:
            event.remove(db.session(), 'after_commit', after_commit)
            event.remove(db.engine, 'before_cursor_execute', before_execute)
        self.assertEqual(status, 200)
        self.assertEqual(response.json['data']['name'], 'Workout')
        self.assertEqual(late_queries, [])
        db.session.remove()
        self.assertEqual(FitnessSession.query.one().name, 'Workout')
