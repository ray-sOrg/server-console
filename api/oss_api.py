from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from model.image import Image
from config import access_key_id, access_key_secret, bucket_name
import base64
import json
import hmac
import hashlib
import time

oss_api_pb = Blueprint('oss_api', __name__)

upload_path = "wedding/music/"
# region = "oss-cn-chengdu-internal"
region = "oss-cn-chengdu"
service = "oss"
endpoint = f"https://{bucket_name}.{region}.aliyuncs.com"


@oss_api_pb.route('/oss/credentials', methods=['GET'])
@jwt_required()
def get_oss_credentials():
    file_type = request.args.get('type')
    # 根据文件类型动态生成 upload_path
    if file_type == 'music':
        upload_path = "wedding/music/"
    elif file_type == 'image':
        upload_path = "wedding/image/"
    else:
        return jsonify({'error': 'Invalid file type'}), 400

    expire_time = 60000
    now = int(time.time())
    expire_sync_point = now + expire_time
    expiration = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(expire_sync_point))

    policy_dict = {
        "expiration": expiration,
        "conditions": [
            {"bucket": bucket_name},
            ["starts-with", "$key", upload_path]
        ]
    }
    policy = json.dumps(policy_dict).strip()
    policy_encoded = base64.b64encode(policy.encode('utf-8')).decode('utf-8')

    h = hmac.new(access_key_secret.encode('utf-8'), policy_encoded.encode('utf-8'), hashlib.sha1)
    signature = base64.b64encode(h.digest()).decode('utf-8')

    return jsonify({
        'dir': upload_path,
        'host': endpoint,
        'accessId': access_key_id,
        'policy': policy_encoded,
        'signature': signature
    })


@oss_api_pb.route('/oss/images/list', methods=['GET'])
@jwt_required()
def get_oss_images_list():
    page_number = request.args.get('pageNumber', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    keyword = request.args.get('keyword', '', type=str)
    try:
        # 构造查询
        query = Image.query.order_by(Image.upload_time.desc())
        if keyword:
            query = query.filter(Image.name.ilike(f"%{keyword}%"))
        images = query.paginate(page=page_number, per_page=page_size, error_out=False)
        images_list = [{'id': img.id, 'name': img.name, 'path': img.path, 'upload_time': img.upload_time,
                        'last_modified': img.last_modified, 'size': img.size, 'content_type': img.content_type} for img
                       in images.items]
        total = images.total
        return jsonify({"code": 200, "message": "Success", "data": images_list, "total": total}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200
