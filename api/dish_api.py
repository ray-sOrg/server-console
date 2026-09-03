from uuid import uuid4, UUID

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import config
from model.dish import Dish, DishNutrition
from utils.dish_validation import dish_payload


restaurant_engine = create_engine(
    config.DATABASE_RESTAURANT, pool_pre_ping=True, pool_recycle=300,
)
RestaurantSession = sessionmaker(bind=restaurant_engine)
dish_api_pb = Blueprint('dish_api', __name__)


def get_restaurant_session():
    return RestaurantSession()


def response(data=None, code=200, message='Success'):
    # Keep the existing business-code convention for Console callers.
    return jsonify({'code': code, 'message': message, 'data': data}), 200


def server_error():
    current_app.logger.exception('Restaurant dish operation failed')
    return response(code=500, message='菜品操作失败，请稍后重试')


def apply_values(dish, values):
    for field, value in values.items():
        if field == 'nutrition':
            if value is None:
                dish.nutrition = None
            elif dish.nutrition is None:
                dish.nutrition = DishNutrition(**value)
            else:
                for key, nutrient in value.items():
                    setattr(dish.nutrition, key, nutrient)
        else:
            setattr(dish, field, value)


@dish_api_pb.route('/dish/list', methods=['GET'])
def get_dish_list():
    try:
        with get_restaurant_session() as session:
            dishes = session.query(Dish).order_by(Dish.createdAt.desc()).all()
            return response([dish.to_dict() for dish in dishes])
    except Exception:
        return server_error()


@dish_api_pb.route('/dish/<dish_id>', methods=['GET'])
def get_dish(dish_id):
    try:
        dish_id = str(UUID(dish_id))
        with get_restaurant_session() as session:
            dish = session.get(Dish, dish_id)
            if dish is None:
                return response(code=404, message='菜品不存在')
            return response(dish.to_dict())
    except ValueError as exc:
        return response(code=400, message=str(exc))
    except Exception:
        return server_error()


@dish_api_pb.route('/dish', methods=['POST'])
def create_dish():
    try:
        values = dish_payload(request.get_json(silent=True))
        with get_restaurant_session() as session:
            with session.begin():
                dish = Dish(id=values.pop('id', str(uuid4())))
                apply_values(dish, values)
                session.add(dish)
                session.flush()
                result = dish.to_dict()
            return response(result)
    except ValueError as exc:
        return response(code=400, message=str(exc))
    except Exception:
        return server_error()


@dish_api_pb.route('/dish/<dish_id>', methods=['PUT'])
def update_dish(dish_id):
    try:
        dish_id = str(UUID(dish_id))
        with get_restaurant_session() as session:
            with session.begin():
                dish = session.get(Dish, dish_id)
                if dish is None:
                    return response(code=404, message='菜品不存在')
                apply_values(dish, dish_payload(request.get_json(silent=True), dish))
                session.flush()
                result = dish.to_dict()
            return response(result)
    except ValueError as exc:
        return response(code=400, message=str(exc))
    except Exception:
        return server_error()


@dish_api_pb.route('/dish/<dish_id>', methods=['DELETE'])
def delete_dish(dish_id):
    try:
        dish_id = str(UUID(dish_id))
        with get_restaurant_session() as session:
            with session.begin():
                dish = session.get(Dish, dish_id)
                if dish is None:
                    return response(code=404, message='菜品不存在')
                session.delete(dish)
            return response({})
    except ValueError as exc:
        return response(code=400, message=str(exc))
    except Exception:
        return server_error()


@dish_api_pb.route('/dish/<dish_id>/toggle', methods=['POST'])
def toggle_dish_availability(dish_id):
    try:
        dish_id = str(UUID(dish_id))
        with get_restaurant_session() as session:
            with session.begin():
                dish = session.get(Dish, dish_id)
                if dish is None:
                    return response(code=404, message='菜品不存在')
                dish.isAvailable = not dish.isAvailable
                session.flush()
                result = dish.to_dict()
            return response(result)
    except ValueError as exc:
        return response(code=400, message=str(exc))
    except Exception:
        return server_error()
