from datetime import datetime

from extensions import db

FITNESS_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FitnessExercise(db.Model):
    __tablename__ = 'fitness_exercise'
    __table_args__ = (
        db.UniqueConstraint('user_identity', 'name', name='uq_fitness_exercise_user_name'),
        db.CheckConstraint(
            "category IN ('strength', 'skill', 'cardio', 'mobility', 'recovery')",
            name='ck_fitness_exercise_category',
        ),
        db.CheckConstraint(
            "metric_type IN ('reps', 'duration', 'distance', 'check')",
            name='ck_fitness_exercise_metric_type',
        ),
    )

    id = db.Column(FITNESS_ID, primary_key=True, autoincrement=True)
    user_identity = db.Column(db.String(100), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(20), nullable=False, default='strength')
    primary_muscle = db.Column(db.String(80), nullable=True)
    secondary_muscles = db.Column(db.Text, nullable=True)
    equipment = db.Column(db.String(160), nullable=True)
    metric_type = db.Column(db.String(20), nullable=False, default='reps')
    instructions = db.Column(db.Text, nullable=True)
    cautions = db.Column(db.Text, nullable=True)
    progression_notes = db.Column(db.Text, nullable=True)
    media = db.Column(db.JSON, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'category': self.category,
            'primaryMuscle': self.primary_muscle,
            'secondaryMuscles': self.secondary_muscles,
            'equipment': self.equipment,
            'metricType': self.metric_type,
            'instructions': self.instructions,
            'cautions': self.cautions,
            'progressionNotes': self.progression_notes,
            'media': self.media,
            'isActive': self.is_active,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
