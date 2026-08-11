from datetime import datetime

from extensions import db

FITNESS_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FitnessPlan(db.Model):
    __tablename__ = 'fitness_plan'
    __table_args__ = (
        db.CheckConstraint('duration_weeks BETWEEN 1 AND 104', name='ck_fitness_plan_duration'),
        db.Index('idx_fitness_plan_user_active', 'user_identity', 'is_active'),
    )

    id = db.Column(FITNESS_ID, primary_key=True, autoincrement=True)
    user_identity = db.Column(db.String(100), nullable=False, index=True)
    tracked_person_id = db.Column(
        db.Integer,
        db.ForeignKey('tracked_person.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration_weeks = db.Column(db.Integer, nullable=False, default=12)
    start_date = db.Column(db.Date, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    days = db.relationship(
        'FitnessPlanDay',
        back_populates='plan',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='FitnessPlanDay.weekday',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'trackedPersonId': self.tracked_person_id,
            'name': self.name,
            'description': self.description,
            'durationWeeks': self.duration_weeks,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'isActive': self.is_active,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
