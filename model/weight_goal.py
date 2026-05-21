from datetime import date, datetime
from decimal import Decimal

from extensions import db


class WeightGoal(db.Model):
    __tablename__ = 'weight_goal'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_identity = db.Column(db.String(100), nullable=False, index=True)
    tracked_person_id = db.Column(db.Integer, db.ForeignKey('tracked_person.id'), nullable=True, index=True)
    start_weight = db.Column(db.Numeric(6, 2), nullable=False)
    target_weight = db.Column(db.Numeric(6, 2), nullable=False)
    target_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(
        self,
        user_identity: str,
        start_weight: Decimal,
        target_weight: Decimal,
        tracked_person_id: int | None = None,
        target_date: date | None = None,
    ):
        self.user_identity = user_identity
        self.tracked_person_id = tracked_person_id
        self.start_weight = start_weight
        self.target_weight = target_weight
        self.target_date = target_date

    def to_dict(self):
        return {
            'id': self.id,
            'userIdentity': self.user_identity,
            'trackedPersonId': self.tracked_person_id,
            'startWeight': float(self.start_weight) if self.start_weight is not None else None,
            'targetWeight': float(self.target_weight) if self.target_weight is not None else None,
            'targetDate': self.target_date.isoformat() if self.target_date else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
