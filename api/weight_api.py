from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import db
from model.weight_record import WeightRecord

weight_api_pb = Blueprint('weight_api', __name__)


def parse_decimal(value, field_name, required=False):
    if value is None or value == '':
        if required:
            raise ValueError(f'{field_name} is required')
        return None

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f'{field_name} must be a number')


def parse_record_date(value):
    if not value:
        return date.today()

    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError('recordDate must be YYYY-MM-DD')


def get_current_user_identity():
    return get_jwt_identity()


@weight_api_pb.route('/weight/record/add', methods=['POST'])
@jwt_required()
def add_weight_record():
    data = request.get_json() or {}

    try:
        record = WeightRecord(
            user_identity=get_current_user_identity(),
            weight=parse_decimal(data.get('weight'), 'weight', required=True),
            record_date=parse_record_date(data.get('recordDate')),
            body_fat=parse_decimal(data.get('bodyFat'), 'bodyFat'),
            bmi=parse_decimal(data.get('bmi'), 'bmi'),
            note=data.get('note')
        )

        db.session.add(record)
        db.session.commit()
        return jsonify({"code": 200, "message": "Success", "data": record.to_dict()}), 200
    except ValueError as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@weight_api_pb.route('/weight/record/edit', methods=['POST'])
@jwt_required()
def edit_weight_record():
    data = request.get_json() or {}
    record_id = data.get('id')

    if not record_id:
        return jsonify({"code": 500, "message": "id is required", "data": {}}), 200

    try:
        record = WeightRecord.query.filter_by(
            id=record_id,
            user_identity=get_current_user_identity()
        ).first()

        if not record:
            return jsonify({"code": 404, "message": "Weight record not found", "data": {}}), 200

        if 'weight' in data:
            record.weight = parse_decimal(data.get('weight'), 'weight', required=True)
        if 'recordDate' in data:
            record.record_date = parse_record_date(data.get('recordDate'))
        if 'bodyFat' in data:
            record.body_fat = parse_decimal(data.get('bodyFat'), 'bodyFat')
        if 'bmi' in data:
            record.bmi = parse_decimal(data.get('bmi'), 'bmi')
        if 'note' in data:
            record.note = data.get('note')

        record.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"code": 200, "message": "Success", "data": record.to_dict()}), 200
    except ValueError as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@weight_api_pb.route('/weight/record/delete', methods=['POST'])
@jwt_required()
def delete_weight_record():
    data = request.get_json() or {}
    record_id = data.get('id')

    if not record_id:
        return jsonify({"code": 500, "message": "id is required", "data": {}}), 200

    try:
        record = WeightRecord.query.filter_by(
            id=record_id,
            user_identity=get_current_user_identity()
        ).first()

        if not record:
            return jsonify({"code": 404, "message": "Weight record not found", "data": {}}), 200

        db.session.delete(record)
        db.session.commit()
        return jsonify({"code": 200, "message": "Success", "data": {"id": record_id}}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@weight_api_pb.route('/weight/records', methods=['GET'])
@jwt_required()
def get_weight_records():
    page_number = request.args.get('pageNumber', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    try:
        query = WeightRecord.query.filter_by(
            user_identity=get_current_user_identity()
        ).order_by(WeightRecord.record_date.desc(), WeightRecord.created_at.desc())

        if start_date:
            query = query.filter(WeightRecord.record_date >= parse_record_date(start_date))
        if end_date:
            query = query.filter(WeightRecord.record_date <= parse_record_date(end_date))

        records = query.paginate(page=page_number, per_page=page_size, error_out=False)
        return jsonify({
            "code": 200,
            "message": "Success",
            "data": [record.to_dict() for record in records.items],
            "total": records.total
        }), 200
    except ValueError as e:
        return jsonify({"code": 500, "message": str(e), "data": [], "total": 0}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": [], "total": 0}), 200


@weight_api_pb.route('/weight/records/all', methods=['GET'])
@jwt_required()
def get_all_weight_records():
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    try:
        query = WeightRecord.query.filter_by(
            user_identity=get_current_user_identity()
        ).order_by(WeightRecord.record_date.asc(), WeightRecord.created_at.asc())

        if start_date:
            query = query.filter(WeightRecord.record_date >= parse_record_date(start_date))
        if end_date:
            query = query.filter(WeightRecord.record_date <= parse_record_date(end_date))

        records = query.all()
        return jsonify({
            "code": 200,
            "message": "Success",
            "data": [record.to_dict() for record in records],
            "total": len(records)
        }), 200
    except ValueError as e:
        return jsonify({"code": 500, "message": str(e), "data": [], "total": 0}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": [], "total": 0}), 200


@weight_api_pb.route('/weight/record/latest', methods=['GET'])
@jwt_required()
def get_latest_weight_record():
    record = WeightRecord.query.filter_by(
        user_identity=get_current_user_identity()
    ).order_by(WeightRecord.record_date.desc(), WeightRecord.created_at.desc()).first()

    return jsonify({
        "code": 200,
        "message": "Success",
        "data": record.to_dict() if record else {}
    }), 200


@weight_api_pb.route('/weight/summary', methods=['GET'])
@jwt_required()
def get_weight_summary():
    days = request.args.get('days', 30, type=int)
    if days <= 0:
        days = 30

    start_date = date.today() - timedelta(days=days - 1)
    records = WeightRecord.query.filter(
        WeightRecord.user_identity == get_current_user_identity(),
        WeightRecord.record_date >= start_date
    ).order_by(WeightRecord.record_date.asc(), WeightRecord.created_at.asc()).all()

    if not records:
        return jsonify({
            "code": 200,
            "message": "Success",
            "data": {
                "count": 0,
                "days": days,
                "latest": None,
                "earliest": None,
                "change": 0,
                "minWeight": None,
                "maxWeight": None,
                "avgWeight": None
            }
        }), 200

    weights = [record.weight for record in records]
    earliest = records[0]
    latest = records[-1]
    avg_weight = sum(weights) / len(weights)

    return jsonify({
        "code": 200,
        "message": "Success",
        "data": {
            "count": len(records),
            "days": days,
            "latest": latest.to_dict(),
            "earliest": earliest.to_dict(),
            "change": float(latest.weight - earliest.weight),
            "minWeight": float(min(weights)),
            "maxWeight": float(max(weights)),
            "avgWeight": round(float(avg_weight), 2)
        }
    }), 200
