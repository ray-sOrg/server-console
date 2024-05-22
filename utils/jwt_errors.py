from flask import jsonify
from extensions import jwt


def register_jwt_errors():
    # 设置过期令牌的错误处理程序
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        response_data = {"code": 5001, "message": "The token has expired", "data": {}}
        return jsonify(response_data), 200

    # 设置无效令牌的错误处理程序
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        response_data = {"code": 5002, "message": "Invalid token", "data": {}}
        return jsonify(response_data), 200

    # 设置未授权的错误处理程序
    @jwt.unauthorized_loader
    def unauthorized_callback(error):
        response_data = {"code": 5003, "message": "Missing Authorization Header", "data": {}}
        return jsonify(response_data), 200

    # 设置需要新鲜令牌的错误处理程序
    @jwt.needs_fresh_token_loader
    def needs_fresh_token_callback(jwt_header, jwt_payload):
        response_data = {"code": 5004, "message": "Fresh token required", "data": {}}
        return jsonify(response_data), 200

    # 设置撤销令牌的错误处理程序
    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        response_data = {"code": 5005, "message": "Token has been revoked", "data": {}}
        return jsonify(response_data), 200
