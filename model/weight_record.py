from datetime import date, datetime
from decimal import Decimal

from extensions import db


class WeightRecord(db.Model):
    __tablename__ = 'weight_record'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_identity = db.Column(db.String(100), nullable=False, index=True)
    tracked_person_id = db.Column(db.Integer, db.ForeignKey('tracked_person.id'), nullable=True, index=True)
    weight = db.Column(db.Numeric(6, 2), nullable=False)
    record_date = db.Column(db.Date, nullable=False, index=True)
    body_fat = db.Column(db.Numeric(5, 2), nullable=True)
    bmi = db.Column(db.Numeric(5, 2), nullable=True)
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __init__(
        self,
        user_identity: str,
        weight: Decimal,
        record_date: date,
        tracked_person_id: int | None = None,
        body_fat: Decimal | None = None,
        bmi: Decimal | None = None,
        note: str | None = None,
    ):
        self.user_identity = user_identity
        self.tracked_person_id = tracked_person_id
        self.weight = weight
        self.record_date = record_date
        self.body_fat = body_fat
        self.bmi = bmi
        self.note = note

    def to_dict(self):
        return {
            'id': self.id,
            'userIdentity': self.user_identity,
            'trackedPersonId': self.tracked_person_id,
            'weight': float(self.weight) if self.weight is not None else None,
            'recordDate': self.record_date.isoformat() if self.record_date else None,
            'bodyFat': float(self.body_fat) if self.body_fat is not None else None,
            'bmi': float(self.bmi) if self.bmi is not None else None,
            'note': self.note,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
