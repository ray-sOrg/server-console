from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from model.fitness_exercise import FitnessExercise
from model.fitness_plan import FitnessPlan
from model.fitness_plan_day import FitnessPlanDay
from model.fitness_plan_exercise import FitnessPlanExercise
from model.fitness_session import FitnessSession
from model.fitness_session_exercise import FitnessSessionExercise
from model.fitness_set import FitnessSet
from model.tracked_person import TrackedPerson
from utils.fitness_seed import ensure_default_fitness_data


fitness_api_pb = Blueprint('fitness_api', __name__)

EXERCISE_CATEGORIES = {'strength', 'skill', 'cardio', 'mobility', 'recovery'}
METRIC_TYPES = {'reps', 'duration', 'distance', 'check'}


def success(data, total=None):
    payload = {'code': 200, 'message': 'Success', 'data': data}
    if total is not None:
        payload['total'] = total
    return jsonify(payload), 200


def failure(message, code=500, data=None):
    return jsonify({'code': code, 'message': message, 'data': data or {}}), 200


def parse_int(value, field_name, minimum=None, maximum=None, required=False):
    if value is None or value == '':
        if required:
            raise ValueError(f'{field_name} is required')
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field_name} must be an integer')
    if minimum is not None and parsed < minimum:
        raise ValueError(f'{field_name} must be at least {minimum}')
    if maximum is not None and parsed > maximum:
        raise ValueError(f'{field_name} must be at most {maximum}')
    return parsed


def parse_decimal(value, field_name):
    if value is None or value == '':
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{field_name} must be a number')


def parse_optional_date(value, field_name):
    if value is None or value == '':
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f'{field_name} must be YYYY-MM-DD')


def serialize_plan(plan):
    result = plan.to_dict()
    result['days'] = []
    for day in sorted(plan.days, key=lambda item: item.weekday):
        day_result = day.to_dict()
        day_result['exercises'] = [
            item.to_dict() for item in sorted(day.exercises, key=lambda item: item.sort_order)
        ]
        result['days'].append(day_result)
    return result


def previous_sets_by_exercise(session):
    exercise_ids = {
        item.exercise_id for item in session.exercises if item.exercise_id is not None
    }
    if not exercise_ids:
        return {}
    rows = FitnessSessionExercise.query.join(
        FitnessSession,
        FitnessSessionExercise.session_id == FitnessSession.id,
    ).filter(
        FitnessSession.user_identity == session.user_identity,
        FitnessSession.subject_key == session.subject_key,
        FitnessSession.scheduled_date < session.scheduled_date,
        FitnessSessionExercise.exercise_id.in_(exercise_ids),
    ).order_by(
        FitnessSessionExercise.exercise_id.asc(),
        FitnessSession.scheduled_date.desc(),
        FitnessSession.created_at.desc(),
    ).all()
    latest = {}
    for exercise in rows:
        if exercise.exercise_id in latest:
            continue
        completed_sets = [item.to_dict() for item in exercise.sets if item.completed]
        if completed_sets:
            latest[exercise.exercise_id] = completed_sets
    return latest


def serialize_session(session, include_previous=False):
    result = session.to_dict()
    result['exercises'] = []
    previous_sets = previous_sets_by_exercise(session) if include_previous else {}
    for exercise in sorted(session.exercises, key=lambda item: item.sort_order):
        exercise_result = exercise.to_dict()
        exercise_result['sets'] = [
            item.to_dict() for item in sorted(exercise.sets, key=lambda item: item.set_number)
        ]
        exercise_result['previousSets'] = previous_sets.get(exercise.exercise_id, [])
        result['exercises'].append(exercise_result)
    result.update(session_progress(session))
    return result


def session_progress(session):
    sets = [item for exercise in session.exercises for item in exercise.sets]
    completed_sets = sum(1 for item in sets if item.completed)
    total_volume = sum(
        float(item.actual_weight_kg) * item.actual_reps
        for item in sets
        if item.completed and item.actual_weight_kg is not None and item.actual_reps is not None
    )
    return {
        'completedSets': completed_sets,
        'totalSets': len(sets),
        'progressPercent': round(completed_sets / len(sets) * 100) if sets else 0,
        'totalVolumeKg': round(total_volume, 1),
    }


def serialize_session_summary(session):
    result = session.to_dict()
    result.update(session_progress(session))
    result['exerciseCount'] = len(session.exercises)
    if session.ended_at and session.started_at:
        result['durationMinutes'] = max(
            0,
            round((session.ended_at - session.started_at).total_seconds() / 60),
        )
    else:
        result['durationMinutes'] = None
    return result


def owned_plan(plan_id, user_identity):
    plan = FitnessPlan.query.filter_by(id=plan_id, user_identity=user_identity).first()
    if not plan:
        raise ValueError('Fitness plan not found')
    return plan


def owned_session(session_id, user_identity):
    session = FitnessSession.query.filter_by(
        id=session_id,
        user_identity=user_identity,
    ).first()
    if not session:
        raise ValueError('Fitness session not found')
    return session


def validate_tracked_person(person_id, user_identity):
    if person_id is None or person_id == '':
        return None
    parsed_id = parse_int(person_id, 'trackedPersonId', minimum=1, required=True)
    person = TrackedPerson.query.filter_by(id=parsed_id, user_identity=user_identity).first()
    if not person:
        raise ValueError('trackedPersonId is invalid')
    return person


def apply_session_feedback(session, data):
    notes = (data.get('notes') or '').strip()
    pain_notes = (data.get('painNotes') or '').strip()
    if len(notes) > 2000:
        raise ValueError('notes must be 2000 characters or less')
    if len(pain_notes) > 1000:
        raise ValueError('painNotes must be 1000 characters or less')
    session.notes = notes or None
    session.readiness_score = parse_int(data.get('readinessScore'), 'readinessScore', 1, 5)
    session.effort_score = parse_int(data.get('effortScore'), 'effortScore', 1, 10)
    session.pain_flag = bool(data.get('painFlag', False))
    session.pain_notes = pain_notes or None


@fitness_api_pb.route('/fitness/bootstrap', methods=['GET'])
@jwt_required()
def get_fitness_bootstrap():
    user_identity = get_jwt_identity()
    try:
        ensure_default_fitness_data(db, user_identity)
        exercises = FitnessExercise.query.filter_by(
            user_identity=user_identity
        ).order_by(FitnessExercise.is_active.desc(), FitnessExercise.name.asc()).all()
        plans = FitnessPlan.query.filter_by(
            user_identity=user_identity
        ).order_by(FitnessPlan.is_active.desc(), FitnessPlan.created_at.asc()).all()
        active_plan = next((plan for plan in plans if plan.is_active), plans[0] if plans else None)
        today_session = FitnessSession.query.filter_by(
            user_identity=user_identity,
            subject_key='self',
            scheduled_date=date.today(),
        ).first()
        return success({
            'today': date.today().isoformat(),
            'todayWeekday': date.today().isoweekday(),
            'exercises': [exercise.to_dict() for exercise in exercises],
            'plans': [serialize_plan(plan) for plan in plans],
            'activePlanId': active_plan.id if active_plan else None,
            'todaySession': serialize_session(today_session, include_previous=True)
            if today_session else None,
        })
    except Exception as error:
        db.session.rollback()
        return failure(str(error), data={'exercises': [], 'plans': []})


@fitness_api_pb.route('/fitness/exercise/save', methods=['POST'])
@jwt_required()
def save_fitness_exercise():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return failure('name is required')
    if len(name) > 120:
        return failure('name must be 120 characters or less')

    category = data.get('category') or 'strength'
    metric_type = data.get('metricType') or 'reps'
    if category not in EXERCISE_CATEGORIES:
        return failure('category is invalid')
    if metric_type not in METRIC_TYPES:
        return failure('metricType is invalid')

    try:
        exercise_id = data.get('id')
        duplicate_query = FitnessExercise.query.filter_by(
            user_identity=user_identity,
            name=name,
        )
        if exercise_id:
            duplicate_query = duplicate_query.filter(FitnessExercise.id != exercise_id)
        if duplicate_query.first():
            return failure('已有同名动作')

        if exercise_id:
            exercise = FitnessExercise.query.filter_by(
                id=exercise_id,
                user_identity=user_identity,
            ).first()
            if not exercise:
                return failure('Exercise not found', code=404)
        else:
            exercise = FitnessExercise(user_identity=user_identity)
            db.session.add(exercise)

        exercise.name = name
        exercise.category = category
        exercise.primary_muscle = (data.get('primaryMuscle') or '').strip() or None
        exercise.secondary_muscles = (data.get('secondaryMuscles') or '').strip() or None
        exercise.equipment = (data.get('equipment') or '').strip() or None
        exercise.metric_type = metric_type
        exercise.instructions = (data.get('instructions') or '').strip() or None
        exercise.cautions = (data.get('cautions') or '').strip() or None
        exercise.progression_notes = (data.get('progressionNotes') or '').strip() or None
        exercise.is_active = bool(data.get('isActive', True))
        db.session.commit()
        return success(exercise.to_dict())
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/exercise/archive', methods=['POST'])
@jwt_required()
def archive_fitness_exercise():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        exercise = FitnessExercise.query.filter_by(
            id=parse_int(data.get('id'), 'id', minimum=1, required=True),
            user_identity=user_identity,
        ).first()
        if not exercise:
            return failure('Exercise not found', code=404)
        exercise.is_active = False
        db.session.commit()
        return success(exercise.to_dict())
    except ValueError as error:
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/plan/save', methods=['POST'])
@jwt_required()
def save_fitness_plan():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return failure('name is required')

    try:
        plan_id = data.get('id')
        plan = owned_plan(plan_id, user_identity) if plan_id else FitnessPlan(user_identity=user_identity)
        if not plan_id:
            db.session.add(plan)

        tracked_person = validate_tracked_person(data.get('trackedPersonId'), user_identity)
        duration_weeks = parse_int(data.get('durationWeeks', 12), 'durationWeeks', 1, 104, True)
        days_payload = data.get('days') or []
        weekdays = [parse_int(item.get('weekday'), 'weekday', 1, 7, True) for item in days_payload]
        if len(weekdays) != len(set(weekdays)):
            raise ValueError('weekday must be unique within a plan')

        exercise_ids = {
            parse_int(item.get('exerciseId'), 'exerciseId', 1, required=True)
            for day in days_payload
            for item in (day.get('exercises') or [])
        }
        owned_exercises = FitnessExercise.query.filter(
            FitnessExercise.user_identity == user_identity,
            FitnessExercise.id.in_(exercise_ids),
        ).all() if exercise_ids else []
        exercise_map = {exercise.id: exercise for exercise in owned_exercises}
        if len(exercise_map) != len(exercise_ids):
            raise ValueError('One or more exercises are invalid')

        plan.name = name[:120]
        plan.description = (data.get('description') or '').strip() or None
        plan.duration_weeks = duration_weeks
        plan.start_date = parse_optional_date(data.get('startDate'), 'startDate')
        plan.tracked_person_id = tracked_person.id if tracked_person else None
        should_activate = bool(data.get('isActive', plan.is_active))
        if should_activate:
            db.session.flush()
            FitnessPlan.query.filter(
                FitnessPlan.user_identity == user_identity,
                FitnessPlan.id != plan.id,
            ).update({'is_active': False}, synchronize_session=False)
        plan.is_active = should_activate

        if plan.id:
            plan.days.clear()
            db.session.flush()

        for day_data in days_payload:
            weekday = parse_int(day_data.get('weekday'), 'weekday', 1, 7, True)
            day = FitnessPlanDay(
                plan=plan,
                weekday=weekday,
                name=((day_data.get('name') or f'星期{weekday}').strip())[:120],
                focus=(day_data.get('focus') or '').strip() or None,
                is_rest=bool(day_data.get('isRest', False)),
                estimated_minutes=parse_int(
                    day_data.get('estimatedMinutes'),
                    'estimatedMinutes',
                    0,
                    480,
                ),
                notes=(day_data.get('notes') or '').strip() or None,
            )
            db.session.add(day)
            for sort_order, item_data in enumerate(day_data.get('exercises') or [], start=1):
                exercise_id = parse_int(item_data.get('exerciseId'), 'exerciseId', 1, required=True)
                item = FitnessPlanExercise(
                    plan_day=day,
                    exercise=exercise_map[exercise_id],
                    sort_order=sort_order,
                    sets=parse_int(item_data.get('sets'), 'sets', 1, 20),
                    reps_min=parse_int(item_data.get('repsMin'), 'repsMin', 0, 1000),
                    reps_max=parse_int(item_data.get('repsMax'), 'repsMax', 0, 1000),
                    duration_seconds_min=parse_int(
                        item_data.get('durationSecondsMin'), 'durationSecondsMin', 0, 86400
                    ),
                    duration_seconds_max=parse_int(
                        item_data.get('durationSecondsMax'), 'durationSecondsMax', 0, 86400
                    ),
                    rir_min=parse_int(item_data.get('rirMin'), 'rirMin', 0, 10),
                    rir_max=parse_int(item_data.get('rirMax'), 'rirMax', 0, 10),
                    target_weight_kg=parse_decimal(item_data.get('targetWeightKg'), 'targetWeightKg'),
                    weight_note=(item_data.get('weightNote') or '').strip() or None,
                    rest_seconds=parse_int(item_data.get('restSeconds'), 'restSeconds', 0, 3600),
                    progression_type=(item_data.get('progressionType') or '').strip() or None,
                    plan_notes=(item_data.get('planNotes') or '').strip() or None,
                    superset_group=(item_data.get('supersetGroup') or '').strip() or None,
                    each_side=bool(item_data.get('eachSide', False)),
                )
                if item.reps_min is not None and item.reps_max is not None and item.reps_min > item.reps_max:
                    raise ValueError('repsMin cannot exceed repsMax')
                if (
                    item.duration_seconds_min is not None
                    and item.duration_seconds_max is not None
                    and item.duration_seconds_min > item.duration_seconds_max
                ):
                    raise ValueError('durationSecondsMin cannot exceed durationSecondsMax')
                db.session.add(item)

        db.session.commit()
        return success(serialize_plan(plan))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/plan/activate', methods=['POST'])
@jwt_required()
def activate_fitness_plan():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        plan = owned_plan(parse_int(data.get('id'), 'id', 1, required=True), user_identity)
        FitnessPlan.query.filter_by(user_identity=user_identity).update(
            {'is_active': False}, synchronize_session=False
        )
        plan.is_active = True
        db.session.commit()
        return success(serialize_plan(plan))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/plan/copy', methods=['POST'])
@jwt_required()
def copy_fitness_plan():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        source = owned_plan(parse_int(data.get('id'), 'id', 1, required=True), user_identity)
        requested_name = (data.get('name') or '').strip()
        copy_name = requested_name or f'{source.name} · 副本'
        if len(copy_name) > 120:
            raise ValueError('name must be 120 characters or less')
        plan = FitnessPlan(
            user_identity=user_identity,
            tracked_person_id=source.tracked_person_id,
            name=copy_name,
            description=source.description,
            duration_weeks=source.duration_weeks,
            start_date=source.start_date,
            is_active=False,
        )
        db.session.add(plan)
        for source_day in source.days:
            day = FitnessPlanDay(
                plan=plan,
                weekday=source_day.weekday,
                name=source_day.name,
                focus=source_day.focus,
                is_rest=source_day.is_rest,
                estimated_minutes=source_day.estimated_minutes,
                notes=source_day.notes,
            )
            db.session.add(day)
            for source_item in source_day.exercises:
                db.session.add(FitnessPlanExercise(
                    plan_day=day,
                    exercise_id=source_item.exercise_id,
                    sort_order=source_item.sort_order,
                    sets=source_item.sets,
                    reps_min=source_item.reps_min,
                    reps_max=source_item.reps_max,
                    duration_seconds_min=source_item.duration_seconds_min,
                    duration_seconds_max=source_item.duration_seconds_max,
                    rir_min=source_item.rir_min,
                    rir_max=source_item.rir_max,
                    target_weight_kg=source_item.target_weight_kg,
                    weight_note=source_item.weight_note,
                    rest_seconds=source_item.rest_seconds,
                    progression_type=source_item.progression_type,
                    plan_notes=source_item.plan_notes,
                    superset_group=source_item.superset_group,
                    each_side=source_item.each_side,
                ))
        db.session.commit()
        return success(serialize_plan(plan))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/plan/delete', methods=['POST'])
@jwt_required()
def delete_fitness_plan():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        plan = owned_plan(parse_int(data.get('id'), 'id', 1, required=True), user_identity)
        remaining_plan = FitnessPlan.query.filter(
            FitnessPlan.user_identity == user_identity,
            FitnessPlan.id != plan.id,
        ).order_by(
            FitnessPlan.is_active.desc(),
            FitnessPlan.created_at.desc(),
        ).first()
        linked_sessions = FitnessSession.query.filter_by(
            user_identity=user_identity,
            plan_id=plan.id,
        ).update(
            {'plan_id': None, 'plan_day_id': None},
            synchronize_session=False,
        )
        if plan.is_active and remaining_plan:
            remaining_plan.is_active = True

        deleted_id = plan.id
        db.session.delete(plan)
        db.session.commit()
        return success({
            'id': deleted_id,
            'activePlanId': remaining_plan.id if remaining_plan else None,
            'preservedSessionCount': linked_sessions,
        })
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/session/start', methods=['POST'])
@jwt_required()
def start_fitness_session():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        scheduled_date = parse_optional_date(data.get('scheduledDate'), 'scheduledDate') or date.today()
        tracked_person = validate_tracked_person(data.get('trackedPersonId'), user_identity)
        subject_key = f'person:{tracked_person.id}' if tracked_person else 'self'
        existing = FitnessSession.query.filter_by(
            user_identity=user_identity,
            subject_key=subject_key,
            scheduled_date=scheduled_date,
        ).first()
        if existing:
            return success(serialize_session(existing, include_previous=True))

        plan = FitnessPlan.query.filter_by(
            user_identity=user_identity,
            is_active=True,
        ).order_by(FitnessPlan.created_at.asc()).first()
        if not plan:
            raise ValueError('No active fitness plan')
        plan_day = next(
            (item for item in plan.days if item.weekday == scheduled_date.isoweekday()),
            None,
        )
        if not plan_day:
            raise ValueError('The active plan has no schedule for this date')

        session = FitnessSession(
            user_identity=user_identity,
            subject_key=subject_key,
            tracked_person_id=tracked_person.id if tracked_person else None,
            plan_id=plan.id,
            plan_day_id=plan_day.id,
            scheduled_date=scheduled_date,
            weekday=scheduled_date.isoweekday(),
            name=plan_day.name,
            focus=plan_day.focus,
            status='in_progress',
        )
        db.session.add(session)

        for plan_item in plan_day.exercises:
            source = plan_item.exercise
            session_exercise = FitnessSessionExercise(
                session=session,
                source_plan_exercise_id=plan_item.id,
                exercise_id=source.id,
                sort_order=plan_item.sort_order,
                exercise_name=source.name,
                category=source.category,
                primary_muscle=source.primary_muscle,
                equipment=source.equipment,
                metric_type=source.metric_type,
                instructions=source.instructions,
                cautions=source.cautions,
                target_sets=plan_item.sets,
                reps_min=plan_item.reps_min,
                reps_max=plan_item.reps_max,
                duration_seconds_min=plan_item.duration_seconds_min,
                duration_seconds_max=plan_item.duration_seconds_max,
                rir_min=plan_item.rir_min,
                rir_max=plan_item.rir_max,
                target_weight_kg=plan_item.target_weight_kg,
                weight_note=plan_item.weight_note,
                rest_seconds=plan_item.rest_seconds,
                progression_type=plan_item.progression_type,
                plan_notes=plan_item.plan_notes,
                superset_group=plan_item.superset_group,
                each_side=plan_item.each_side,
            )
            db.session.add(session_exercise)
            for set_number in range(1, (plan_item.sets or 1) + 1):
                db.session.add(FitnessSet(
                    session_exercise=session_exercise,
                    set_number=set_number,
                ))

        db.session.commit()
        return success(serialize_session(session, include_previous=True))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/session/set/save', methods=['POST'])
@jwt_required()
def save_fitness_set():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        set_id = parse_int(data.get('id'), 'id', 1, required=True)
        fitness_set = FitnessSet.query.join(
            FitnessSessionExercise,
            FitnessSet.session_exercise_id == FitnessSessionExercise.id,
        ).join(
            FitnessSession,
            FitnessSessionExercise.session_id == FitnessSession.id,
        ).filter(
            FitnessSet.id == set_id,
            FitnessSession.user_identity == user_identity,
        ).first()
        if not fitness_set:
            return failure('Fitness set not found', code=404)

        completed = bool(data.get('completed', True))
        actual_reps = parse_int(data.get('actualReps'), 'actualReps', 0, 10000)
        actual_duration = parse_int(
            data.get('actualDurationSeconds'),
            'actualDurationSeconds',
            0,
            86400,
        )
        actual_weight = parse_decimal(data.get('actualWeightKg'), 'actualWeightKg')
        rir = parse_int(data.get('rir'), 'rir', 0, 10)
        metric_type = fitness_set.session_exercise.metric_type
        if completed and metric_type == 'reps' and actual_reps is None:
            raise ValueError('actualReps is required for this exercise')
        if completed and metric_type == 'duration' and actual_duration is None:
            raise ValueError('actualDurationSeconds is required for this exercise')
        if actual_weight is not None and actual_weight < 0:
            raise ValueError('actualWeightKg must be at least 0')

        fitness_set.actual_reps = actual_reps
        fitness_set.actual_duration_seconds = actual_duration
        fitness_set.actual_weight_kg = actual_weight
        fitness_set.rir = rir
        fitness_set.completed = completed
        fitness_set.completed_at = datetime.utcnow() if completed else None
        fitness_set.notes = (data.get('notes') or '').strip() or None

        session_exercise = fitness_set.session_exercise
        db.session.flush()
        session_exercise.completed = all(item.completed for item in session_exercise.sets)
        session = session_exercise.session
        session.status = 'in_progress'
        session.ended_at = None
        db.session.commit()
        return success(serialize_session(session, include_previous=True))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/session/exercise/set/add', methods=['POST'])
@jwt_required()
def add_fitness_set():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        exercise_id = parse_int(
            data.get('exerciseId'),
            'exerciseId',
            1,
            required=True,
        )
        session_exercise = FitnessSessionExercise.query.join(
            FitnessSession,
            FitnessSessionExercise.session_id == FitnessSession.id,
        ).filter(
            FitnessSessionExercise.id == exercise_id,
            FitnessSession.user_identity == user_identity,
        ).first()
        if not session_exercise:
            return failure('Fitness session exercise not found', code=404)
        if session_exercise.session.status != 'in_progress':
            raise ValueError('Only an active workout can add sets')

        next_set_number = max(
            (item.set_number for item in session_exercise.sets),
            default=0,
        ) + 1
        fitness_set = FitnessSet(
            session_exercise=session_exercise,
            set_number=next_set_number,
        )
        db.session.add(fitness_set)
        session_exercise.target_sets = next_set_number
        session_exercise.completed = False
        db.session.commit()
        return success(serialize_session(
            session_exercise.session,
            include_previous=True,
        ))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/session/finish', methods=['POST'])
@jwt_required()
def finish_fitness_session():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        session = owned_session(
            parse_int(data.get('id'), 'id', 1, required=True),
            user_identity,
        )
        sets = [item for exercise in session.exercises for item in exercise.sets]
        completed_count = sum(1 for item in sets if item.completed)
        if sets and completed_count == len(sets):
            session.status = 'completed'
        elif completed_count:
            session.status = 'partial'
        else:
            session.status = 'skipped'
        session.ended_at = datetime.utcnow()
        apply_session_feedback(session, data)
        db.session.commit()
        return success(serialize_session(session, include_previous=True))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/session/feedback/save', methods=['POST'])
@jwt_required()
def save_fitness_session_feedback():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        session = owned_session(
            parse_int(data.get('id'), 'id', 1, required=True),
            user_identity,
        )
        apply_session_feedback(session, data)
        db.session.commit()
        return success(serialize_session(session, include_previous=True))
    except ValueError as error:
        db.session.rollback()
        return failure(str(error))
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/session/delete', methods=['POST'])
@jwt_required()
def delete_fitness_session():
    user_identity = get_jwt_identity()
    data = request.get_json() or {}
    try:
        session = owned_session(
            parse_int(data.get('id'), 'id', 1, required=True),
            user_identity,
        )
        deleted_id = session.id
        db.session.delete(session)
        db.session.commit()
        return success({'id': deleted_id})
    except ValueError as error:
        db.session.rollback()
        return failure(str(error), code=404)
    except Exception as error:
        db.session.rollback()
        return failure(str(error))


@fitness_api_pb.route('/fitness/history', methods=['GET'])
@jwt_required()
def get_fitness_history():
    user_identity = get_jwt_identity()
    try:
        limit = parse_int(request.args.get('limit', 50), 'limit', 1, 100, True)
        sessions = FitnessSession.query.filter_by(
            user_identity=user_identity,
        ).order_by(
            FitnessSession.scheduled_date.desc(),
            FitnessSession.created_at.desc(),
        ).limit(limit).all()
        return success([serialize_session_summary(session) for session in sessions], len(sessions))
    except ValueError as error:
        return failure(str(error), data=[])
    except Exception as error:
        return failure(str(error), data=[])


@fitness_api_pb.route('/fitness/session/<int:session_id>', methods=['GET'])
@jwt_required()
def get_fitness_session(session_id):
    user_identity = get_jwt_identity()
    try:
        return success(serialize_session(owned_session(session_id, user_identity)))
    except ValueError as error:
        return failure(str(error), code=404)
    except Exception as error:
        return failure(str(error))


@fitness_api_pb.route('/fitness/records', methods=['GET'])
@jwt_required()
def get_fitness_records():
    user_identity = get_jwt_identity()
    try:
        rows = db.session.query(
            FitnessSet,
            FitnessSessionExercise,
            FitnessSession,
        ).join(
            FitnessSessionExercise,
            FitnessSet.session_exercise_id == FitnessSessionExercise.id,
        ).join(
            FitnessSession,
            FitnessSessionExercise.session_id == FitnessSession.id,
        ).filter(
            FitnessSession.user_identity == user_identity,
            FitnessSet.completed.is_(True),
        ).all()

        records = {}
        for fitness_set, exercise, session in rows:
            key = exercise.exercise_id or exercise.exercise_name
            record = records.setdefault(key, {
                'exerciseId': exercise.exercise_id,
                'exerciseName': exercise.exercise_name,
                'primaryMuscle': exercise.primary_muscle,
                'maxWeightKg': None,
                'maxReps': None,
                'estimatedOneRepMaxKg': None,
                'maxSetVolumeKg': None,
                'completedSets': 0,
                'lastRecordDate': None,
                'trend': {},
            })
            weight = float(fitness_set.actual_weight_kg) if fitness_set.actual_weight_kg is not None else None
            reps = fitness_set.actual_reps
            date_key = session.scheduled_date.isoformat()
            record['completedSets'] += 1
            if weight is not None:
                record['maxWeightKg'] = max(record['maxWeightKg'] or 0, weight)
            if reps is not None:
                record['maxReps'] = max(record['maxReps'] or 0, reps)
            if weight is not None and reps:
                estimated = weight * (1 + reps / 30)
                volume = weight * reps
                record['estimatedOneRepMaxKg'] = round(
                    max(record['estimatedOneRepMaxKg'] or 0, estimated),
                    1,
                )
                record['maxSetVolumeKg'] = round(
                    max(record['maxSetVolumeKg'] or 0, volume),
                    1,
                )
            point = record['trend'].setdefault(date_key, {
                'date': date_key,
                'maxWeightKg': None,
                'maxReps': None,
                'estimatedOneRepMaxKg': None,
                'totalVolumeKg': 0,
            })
            if weight is not None:
                point['maxWeightKg'] = max(point['maxWeightKg'] or 0, weight)
            if reps is not None:
                point['maxReps'] = max(point['maxReps'] or 0, reps)
            if weight is not None and reps:
                point['estimatedOneRepMaxKg'] = round(
                    max(point['estimatedOneRepMaxKg'] or 0, weight * (1 + reps / 30)),
                    1,
                )
                point['totalVolumeKg'] = round(point['totalVolumeKg'] + weight * reps, 1)
            record['lastRecordDate'] = max(record['lastRecordDate'] or date_key, date_key)

        for record in records.values():
            record['trend'] = sorted(
                record['trend'].values(),
                key=lambda item: item['date'],
            )[-12:]

        ordered = sorted(
            records.values(),
            key=lambda item: (
                -(item['estimatedOneRepMaxKg'] or 0),
                item['exerciseName'],
            ),
        )
        return success(ordered, len(ordered))
    except Exception as error:
        return failure(str(error), data=[])


@fitness_api_pb.route('/fitness/export', methods=['GET'])
@jwt_required()
def export_fitness_data():
    user_identity = get_jwt_identity()
    try:
        exercises = FitnessExercise.query.filter_by(
            user_identity=user_identity,
        ).order_by(FitnessExercise.name.asc()).all()
        plans = FitnessPlan.query.filter_by(
            user_identity=user_identity,
        ).order_by(FitnessPlan.created_at.asc()).all()
        sessions = FitnessSession.query.filter_by(
            user_identity=user_identity,
        ).order_by(FitnessSession.scheduled_date.asc()).all()
        return success({
            'exportedAt': datetime.utcnow().isoformat() + 'Z',
            'exercises': [item.to_dict() for item in exercises],
            'plans': [serialize_plan(item) for item in plans],
            'sessions': [serialize_session(item) for item in sessions],
        })
    except Exception as error:
        return failure(str(error))
