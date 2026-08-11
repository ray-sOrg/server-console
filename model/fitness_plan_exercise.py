from decimal import Decimal

from extensions import db

FITNESS_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FitnessPlanExercise(db.Model):
    __tablename__ = 'fitness_plan_exercise'
    __table_args__ = (
        db.UniqueConstraint('plan_day_id', 'sort_order', name='uq_fitness_plan_exercise_order'),
        db.CheckConstraint('sort_order > 0', name='ck_fitness_plan_exercise_order'),
        db.CheckConstraint('sets IS NULL OR sets BETWEEN 1 AND 20', name='ck_fitness_plan_exercise_sets'),
        db.CheckConstraint('rest_seconds IS NULL OR rest_seconds BETWEEN 0 AND 3600', name='ck_fitness_plan_exercise_rest'),
    )

    id = db.Column(FITNESS_ID, primary_key=True, autoincrement=True)
    plan_day_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_plan_day.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    exercise_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_exercise.id', ondelete='RESTRICT'),
        nullable=False,
        index=True,
    )
    sort_order = db.Column(db.Integer, nullable=False)
    sets = db.Column(db.Integer, nullable=True)
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

    plan_day = db.relationship('FitnessPlanDay', back_populates='exercises')
    exercise = db.relationship('FitnessExercise', lazy='joined')

    def to_dict(self):
        return {
            'id': self.id,
            'exerciseId': self.exercise_id,
            'sortOrder': self.sort_order,
            'sets': self.sets,
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
            'exercise': self.exercise.to_dict() if self.exercise else None,
        }
