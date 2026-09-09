"""Console-only access to Chuan Dai users bound to unified identities."""
from uuid import UUID

from flask import Blueprint, current_app, request
from sqlalchemy import or_

from api.dish_api import get_restaurant_session, response
from model.restaurant_user import RestaurantUser
from utils.authorization import admin_required


restaurant_user_api_pb = Blueprint('restaurant_user_api', __name__)


def positive_integer(name, default, maximum):
    try:
        value = int(request.args.get(name, default))
    except (TypeError, ValueError):
        raise ValueError(f'{name} 必须为正整数') from None
    if not 1 <= value <= maximum:
        raise ValueError(f'{name} 必须在 1 到 {maximum} 之间')
    return value


@restaurant_user_api_pb.route('/user/list', methods=['GET'])
@admin_required
def get_user_list():
    try:
        page = positive_integer('pageNumber', 1, 1000000)
        size = positive_integer('pageSize', 10, 100)
        keyword = request.args.get('keyword', '').strip()
        role = request.args.get('role', '')
        if len(keyword) > 100:
            raise ValueError('搜索内容不能超过 100 个字符')
        if role not in ('', 'HOST', 'GUEST'):
            raise ValueError('无效的用户角色')

        with get_restaurant_session() as session:
            query = session.query(RestaurantUser)
            if keyword:
                # Treat SQL wildcard characters as literal search text.
                escaped = keyword.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                pattern = f'%{escaped}%'
                query = query.filter(or_(
                    RestaurantUser.account.ilike(pattern, escape='\\'),
                    RestaurantUser.nickname.ilike(pattern, escape='\\'),
                    RestaurantUser.phone.ilike(pattern, escape='\\'),
                ))
            if role:
                query = query.filter(RestaurantUser.role == role)
            total = query.count()
            # Clamp pages after deletions or stale bookmarks.
            page = min(page, max(1, (total + size - 1) // size))
            users = query.order_by(
                RestaurantUser.createdAt.desc(), RestaurantUser.id.asc(),
            ).offset((page - 1) * size).limit(size).all()
            return response({
                'items': [user.to_dict() for user in users],
                'total': total, 'pageNumber': page, 'pageSize': size,
            })
    except ValueError as exc:
        return response(code=400, message=str(exc))
    except Exception:
        current_app.logger.exception('Failed to list restaurant users')
        return response(code=500, message='获取川傣用户失败，请稍后重试')


@restaurant_user_api_pb.route('/user/<user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    try:
        user_id = str(UUID(user_id))
    except ValueError:
        return response(code=400, message='无效的用户 ID')
    try:
        with get_restaurant_session() as session:
            user = session.get(RestaurantUser, user_id)
            if user is None:
                return response(code=404, message='川傣用户不存在')
            return response(user.to_dict())
    except Exception:
        current_app.logger.exception('Failed to read restaurant user')
        return response(code=500, message='获取用户详情失败，请稍后重试')
