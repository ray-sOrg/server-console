from datetime import datetime

from extensions import db


class TrackedPerson(db.Model):
    __tablename__ = 'tracked_person'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_identity = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    height_cm = db.Column(db.Integer, nullable=False)
    birth_date = db.Column(db.Date, nullable=True)
    relationship = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'userIdentity': self.user_identity,
            'name': self.name,
            'heightCm': self.height_cm,
            'birthDate': self.birth_date.isoformat() if self.birth_date else None,
            'relationship': self.relationship,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
