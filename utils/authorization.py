"""Server-side console authorization, independent of UI menu visibility."""
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from model.user import User


def forbidden(message='仅管理员可执行此操作'):
    # Preserve the API's HTTP-200/business-code convention.
    return jsonify({'code': 403, 'message': message, 'data': {}}), 200


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapped(*args, **kwargs):
        # Always read current roles from the DB, not stale JWT role claims.
        user = User.query.filter_by(username=get_jwt_identity()).first()
        if user is None or user.role not in ('admin', 'super_admin'):
            return forbidden()
        g.console_actor = user
        return fn(*args, **kwargs)
    return wrapped
