from decimal import Decimal

from extensions import db


FITNESS_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FitnessSessionExercise(db.Model):
    __tablename__ = 'fitness_session_exercise'
    __table_args__ = (
        db.UniqueConstraint('session_id', 'sort_order', name='uq_fitness_session_exercise_order'),
        db.CheckConstraint('sort_order > 0', name='ck_fitness_session_exercise_order'),
        db.CheckConstraint(
            "metric_type IN ('reps', 'duration', 'distance', 'check')",
            name='ck_fitness_session_exercise_metric_type',
        ),
    )

    id = db.Column(FITNESS_ID, primary_key=True, autoincrement=True)
    session_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_session.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    source_plan_exercise_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_plan_exercise.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    exercise_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_exercise.id', ondelete='SET NULL'),
        nullable=True,
        index=True,
    )
    sort_order = db.Column(db.Integer, nullable=False)
    exercise_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(20), nullable=False)
    primary_muscle = db.Column(db.String(80), nullable=True)
    equipment = db.Column(db.String(160), nullable=True)
    metric_type = db.Column(db.String(20), nullable=False)
    instructions = db.Column(db.Text, nullable=True)
    cautions = db.Column(db.Text, nullable=True)
    target_sets = db.Column(db.Integer, nullable=True)
    reps_min = db.Column(db.Integer, nullable=True)
    reps_max = db.Column(db.Integer, nullable=True)
    duration_seconds_min = db.Column(db.Integer, nullable=True)
    duration_seconds_max = db.Column(db.Integer, nullable=True)
    rir_min = db.Column(db.Integer, nullable=True)
    rir_max = db.Column(db.Integer, nullable=True)
    target_weight_kg = db.Column(db.Numeric(7, 2), nullable=True)
    weight_note = db.Column(db.Text, nullable=True)
    rest_seconds = db.Column(db.Integer, nullable=True)
    progression_type = db.Column(db.String(60), nullable=True)
    plan_notes = db.Column(db.Text, nullable=True)
    superset_group = db.Column(db.String(20), nullable=True)
    each_side = db.Column(db.Boolean, nullable=False, default=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    notes = db.Column(db.Text, nullable=True)

    session = db.relationship('FitnessSession', back_populates='exercises')
    sets = db.relationship(
        'FitnessSet',
        back_populates='session_exercise',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='FitnessSet.set_number',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'sourcePlanExerciseId': self.source_plan_exercise_id,
            'exerciseId': self.exercise_id,
            'sortOrder': self.sort_order,
            'exerciseName': self.exercise_name,
            'category': self.category,
            'primaryMuscle': self.primary_muscle,
            'equipment': self.equipment,
            'metricType': self.metric_type,
            'instructions': self.instructions,
            'cautions': self.cautions,
            'targetSets': self.target_sets,
            'repsMin': self.reps_min,
            'repsMax': self.reps_max,
            'durationSecondsMin': self.duration_seconds_min,
            'durationSecondsMax': self.duration_seconds_max,
            'rirMin': self.rir_min,
            'rirMax': self.rir_max,
            'targetWeightKg': float(self.target_weight_kg)
            if isinstance(self.target_weight_kg, Decimal)
            else self.target_weight_kg,
            'weightNote': self.weight_note,
            'restSeconds': self.rest_seconds,
            'progressionType': self.progression_type,
            'planNotes': self.plan_notes,
            'supersetGroup': self.superset_group,
            'eachSide': self.each_side,
            'completed': self.completed,
            'notes': self.notes,
        }
