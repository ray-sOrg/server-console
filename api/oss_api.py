from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
import datetime
import base64
import json
import hmac
import hashlib


oss_api_pb = Blueprint('oss_api', __name__)

access_key_id = "LTAI5tQtaWvad7oobHnUZZqW"
access_key_secret = "oWjbVLO9HRl0vZb1lsYxoHqWxjM0NF"
bucket_name = "ray321"
upload_path = "wedding/music/"
region = "oss-cn-chengdu-internal"
# region = "oss-cn-chengdu"
service = "oss"
endpoint = f"https://{bucket_name}.{region}.aliyuncs.com"




@oss_api_pb.route('/oss/credentials', methods=['GET'])
@jwt_required()
def get_oss_credentials():
    # 当前时间和日期
    current_time = datetime.datetime.utcnow()
    date_str = current_time.strftime('%Y%m%dT%H%M%SZ')
    date = current_time.strftime('%Y%m%d')

    # 定义 Policy
    expiration = (current_time + datetime.timedelta(hours=1)).isoformat() + "Z"
    policy_document = {
        "expiration": expiration,
        "conditions": [
            {"bucket": bucket_name},
            ["starts-with", "$key", upload_path],
            ["content-length-range", 0, 104857600]  # 文件大小范围
        ]
    }

    # 编码 Policy
    policy = base64.b64encode(json.dumps(policy_document).encode()).decode()

    # 计算 Signature
    def sign(key, msg):
        return hmac.new(key.encode(), msg.encode(), hashlib.sha1).digest()

    # 创建签名
    canonical_request = f"POST\n/\n\nhost:{bucket_name}.{region}.aliyuncs.com\nx-oss-date:{date_str}\n\nhost;x-oss-date"
    string_to_sign = f"AWS4-HMAC-SHA256\n{date_str}\n{date}/{region}/{service}/aws4_request\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
    signing_key = hmac.new(f"AWS4{access_key_secret}".encode(), date.encode(), hashlib.sha256).digest()
    signing_key = hmac.new(signing_key, f"{region}/{service}/aws4_request".encode(), hashlib.sha256).digest()
    signature = base64.b64encode(hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).digest()).decode()

    return jsonify({
        "OSSAccessKeyId": access_key_id,
        "policy": policy,
        "Signature": signature,
        "bucket": bucket_name,
        "endpoint": endpoint,
        "x-oss-signature-version": "OSS4-HMAC-SHA256",
        "x-oss-credential": f"{access_key_id}/{date}/{region}/{service}/aliyun_v4_request",
        "x-oss-date": date_str
    })
