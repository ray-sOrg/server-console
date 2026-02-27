from flask import Blueprint, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from model.dish import Dish
import config

# 创建餐馆数据库引擎
restaurant_engine = create_engine(
    config.DATABASE_RESTAURANT,
    pool_pre_ping=True,
    pool_recycle=300
)
RestaurantSession = sessionmaker(bind=restaurant_engine)

dish_api_pb = Blueprint('dish_api', __name__)


def get_restaurant_session():
    """获取餐馆数据库的 session"""
    return RestaurantSession()


@dish_api_pb.route('/dish/list', methods=['GET'])
def get_dish_list():
    """获取菜品列表"""
    try:
        session = get_restaurant_session()
        dishes = session.query(Dish).order_by(Dish.createdAt.desc()).all()
        result = [d.to_dict() for d in dishes]
        session.close()
        return jsonify({
            "code": 200, 
            "message": "Success", 
            "data": result
        }), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": []}), 200


@dish_api_pb.route('/dish/<dish_id>', methods=['GET'])
def get_dish(dish_id):
    """获取单个菜品详情"""
    try:
        session = get_restaurant_session()
        dish = session.query(Dish).get(dish_id)
        if not dish:
            session.close()
            return jsonify({"code": 404, "message": "Dish not found", "data": {}}), 200
        result = dish.to_dict()
        session.close()
        return jsonify({"code": 200, "message": "Success", "data": result}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@dish_api_pb.route('/dish', methods=['POST'])
def create_dish():
    """创建菜品"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 500, "message": "No input data provided"}), 200
    
    try:
        session = get_restaurant_session()
        dish = Dish(
            id=data.get('id'),
            name=data.get('name'),
            nameEn=data.get('nameEn'),
            description=data.get('description'),
            descEn=data.get('descEn'),
            price=data.get('price'),
            image=data.get('image'),
            category=data.get('category'),
            isSpicy=data.get('isSpicy', False),
            isVegetarian=data.get('isVegetarian', False),
            isAvailable=data.get('isAvailable', True)
        )
        session.add(dish)
        session.commit()
        result = dish.to_dict()
        session.close()
        return jsonify({"code": 200, "message": "Success", "data": result}), 200
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"code": 500, "message": str(e)}), 200


@dish_api_pb.route('/dish/<dish_id>', methods=['PUT'])
def update_dish(dish_id):
    """更新菜品"""
    data = request.get_json()
    if not data:
        return jsonify({"code": 500, "message": "No input data provided"}), 200
    
    try:
        session = get_restaurant_session()
        dish = session.query(Dish).get(dish_id)
        if not dish:
            session.close()
            return jsonify({"code": 404, "message": "Dish not found"}), 200
        
        # 更新字段
        if 'name' in data:
            dish.name = data['name']
        if 'nameEn' in data:
            dish.nameEn = data['nameEn']
        if 'description' in data:
            dish.description = data['description']
        if 'descEn' in data:
            dish.descEn = data['descEn']
        if 'price' in data:
            dish.price = data['price']
        if 'image' in data:
            dish.image = data['image']
        if 'category' in data:
            dish.category = data['category']
        if 'isSpicy' in data:
            dish.isSpicy = data['isSpicy']
        if 'isVegetarian' in data:
            dish.isVegetarian = data['isVegetarian']
        if 'isAvailable' in data:
            dish.isAvailable = data['isAvailable']
        
        session.commit()
        result = dish.to_dict()
        session.close()
        return jsonify({"code": 200, "message": "Success", "data": result}), 200
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"code": 500, "message": str(e)}), 200


@dish_api_pb.route('/dish/<dish_id>', methods=['DELETE'])
def delete_dish(dish_id):
    """删除菜品"""
    try:
        session = get_restaurant_session()
        dish = session.query(Dish).get(dish_id)
        if not dish:
            session.close()
            return jsonify({"code": 404, "message": "Dish not found"}), 200
        
        session.delete(dish)
        session.commit()
        session.close()
        return jsonify({"code": 200, "message": "Success", "data": {}}), 200
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"code": 500, "message": str(e)}), 200


@dish_api_pb.route('/dish/<dish_id>/toggle', methods=['POST'])
def toggle_dish_availability(dish_id):
    """切换菜品上下架状态"""
    try:
        session = get_restaurant_session()
        dish = session.query(Dish).get(dish_id)
        if not dish:
            session.close()
            return jsonify({"code": 404, "message": "Dish not found"}), 200
        
        dish.isAvailable = not dish.isAvailable
        session.commit()
        result = dish.to_dict()
        session.close()
        return jsonify({"code": 200, "message": "Success", "data": result}), 200
    except Exception as e:
        session.rollback()
        session.close()
        return jsonify({"code": 500, "message": str(e)}), 200
