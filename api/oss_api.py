from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
import base64
import json
import hmac
import hashlib
import time


oss_api_pb = Blueprint('oss_api', __name__)

access_key_id = "LTAI5tQtaWvad7oobHnUZZqW"
access_key_secret = "oWjbVLO9HRl0vZb1lsYxoHqWxjM0NF"
bucket_name = "ray321"
upload_path = "wedding/music/"
# region = "oss-cn-chengdu-internal"
region = "oss-cn-chengdu"
service = "oss"
endpoint = f"https://{bucket_name}.{region}.aliyuncs.com"


@oss_api_pb.route('/oss/credentials', methods=['GET'])
@jwt_required()
def get_oss_credentials():
    expire_time = 60
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
