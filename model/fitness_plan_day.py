from extensions import db

FITNESS_ID = db.BigInteger().with_variant(db.Integer, 'sqlite')


class FitnessPlanDay(db.Model):
    __tablename__ = 'fitness_plan_day'
    __table_args__ = (
        db.UniqueConstraint('plan_id', 'weekday', name='uq_fitness_plan_day_weekday'),
        db.CheckConstraint('weekday BETWEEN 1 AND 7', name='ck_fitness_plan_day_weekday'),
        db.CheckConstraint(
            'estimated_minutes IS NULL OR estimated_minutes BETWEEN 0 AND 480',
            name='ck_fitness_plan_day_minutes',
        ),
    )

    id = db.Column(FITNESS_ID, primary_key=True, autoincrement=True)
    plan_id = db.Column(
        FITNESS_ID,
        db.ForeignKey('fitness_plan.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    weekday = db.Column(db.SmallInteger, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    focus = db.Column(db.String(160), nullable=True)
    is_rest = db.Column(db.Boolean, nullable=False, default=False)
    estimated_minutes = db.Column(db.Integer, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    plan = db.relationship('FitnessPlan', back_populates='days')
    exercises = db.relationship(
        'FitnessPlanExercise',
        back_populates='plan_day',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='FitnessPlanExercise.sort_order',
    )

    def to_dict(self):
        return {
            'id': self.id,
            'weekday': self.weekday,
            'name': self.name,
            'focus': self.focus,
            'isRest': self.is_rest,
            'estimatedMinutes': self.estimated_minutes,
            'notes': self.notes,
        }
