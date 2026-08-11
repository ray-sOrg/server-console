from datetime import datetime

from extensions import db


FITNESS_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FitnessSession(db.Model):
    __tablename__ = 'fitness_session'
    __table_args__ = (
        db.UniqueConstraint(
            'user_identity',
            'subject_key',
            'scheduled_date',
            name='uq_fitness_session_user_subject_date',
        ),
        db.CheckConstraint(
            "status IN ('in_progress', 'completed', 'partial', 'skipped')",
            name='ck_fitness_session_status',
        ),
        db.CheckConstraint('weekday BETWEEN 1 AND 7', name='ck_fitness_session_weekday'),
        db.CheckConstraint(
            'readiness_score IS NULL OR readiness_score BETWEEN 1 AND 5',
            name='ck_fitness_session_readiness',
        ),
        db.CheckConstraint(
            'effort_score IS NULL OR effort_score BETWEEN 1 AND 10',
            name='ck_fitness_session_effort',
        ),
        db.Index('idx_fitness_session_user_date', 'user_identity', 'scheduled_date'),
        db.Index('idx_fitness_session_user_status', 'user_identity', 'status'),
    )

    id = db.Column(FITNESS_ID, primary_key=True, autoincrement=True)
    user_identity = db.Column(db.String(100), nullable=False, index=True)
    subject_key = db.Column(db.String(120), nullable=False, default='self')
    tracked_person_id = db.Column(
        db.Integer,
        db.ForeignKey('tracked_person.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    plan_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_plan.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    plan_day_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_plan_day.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    scheduled_date = db.Column(db.Date, nullable=False)
    weekday = db.Column(db.SmallInteger, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    focus = db.Column(db.String(160), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='in_progress')
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    readiness_score = db.Column(db.SmallInteger, nullable=True)
    effort_score = db.Column(db.SmallInteger, nullable=True)
    pain_flag = db.Column(db.Boolean, nullable=False, default=False)
    pain_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    exercises = db.relationship(
        'FitnessSessionExercise',
        back_populates='session',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='FitnessSessionExercise.sort_order',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'trackedPersonId': self.tracked_person_id,
            'planId': self.plan_id,
            'planDayId': self.plan_day_id,
            'scheduledDate': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'weekday': self.weekday,
            'name': self.name,
            'focus': self.focus,
            'status': self.status,
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'endedAt': self.ended_at.isoformat() if self.ended_at else None,
            'notes': self.notes,
            'readinessScore': self.readiness_score,
            'effortScore': self.effort_score,
            'painFlag': self.pain_flag,
            'painNotes': self.pain_notes,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
