from datetime import datetime
from decimal import Decimal

from extensions import db


FITNESS_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FitnessSet(db.Model):
    __tablename__ = 'fitness_set'
    __table_args__ = (
        db.UniqueConstraint(
            'session_exercise_id',
            'set_number',
            name='uq_fitness_set_exercise_number',
        ),
        db.CheckConstraint('set_number > 0', name='ck_fitness_set_number'),
        db.CheckConstraint('actual_reps IS NULL OR actual_reps >= 0', name='ck_fitness_set_reps'),
        db.CheckConstraint(
            'actual_duration_seconds IS NULL OR actual_duration_seconds >= 0',
            name='ck_fitness_set_duration',
        ),
        db.CheckConstraint(
            'actual_weight_kg IS NULL OR actual_weight_kg >= 0',
            name='ck_fitness_set_weight',
        ),
        db.CheckConstraint('rir IS NULL OR rir BETWEEN 0 AND 10', name='ck_fitness_set_rir'),
    )

    id = db.Column(FITNESS_ID, primary_key=True, autoincrement=True)
    session_exercise_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_session_exercise.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    set_number = db.Column(db.Integer, nullable=False)
    actual_reps = db.Column(db.Integer, nullable=True)
    actual_duration_seconds = db.Column(db.Integer, nullable=True)
    actual_weight_kg = db.Column(db.Numeric(7, 2), nullable=True)
    rir = db.Column(db.Integer, nullable=True)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    deferred_at = db.Column(db.DateTime(timezone=True), nullable=True)
    activated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    session_exercise = db.relationship('FitnessSessionExercise', back_populates='sets')

    def to_dict(self):
        return {
            'id': self.id,
            'setNumber': self.set_number,
            'actualReps': self.actual_reps,
            'actualDurationSeconds': self.actual_duration_seconds,
            'actualWeightKg': float(self.actual_weight_kg)
            if isinstance(self.actual_weight_kg, Decimal)
            else self.actual_weight_kg,
            'rir': self.rir,
            'completed': self.completed,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
            'deferredAt': self.deferred_at.isoformat() if self.deferred_at else None,
            'activatedAt': self.activated_at.isoformat() if self.activated_at else None,
            'notes': self.notes,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
