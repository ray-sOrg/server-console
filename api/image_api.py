from flask import current_app, Blueprint, jsonify
from flask_jwt_extended import jwt_required
from utils.oss_utils import OSSClient
from model.image import Image
from config import access_key_id, access_key_secret, endpoint, bucket_name
from datetime import datetime
from extensions import db
from celery.utils.log import get_task_logger
import os

image_api_pb = Blueprint('image_api', __name__)

logger = get_task_logger(__name__)


def fetch_images_from_oss():
    try:
        # Initialize OSS client
        oss_client = OSSClient(access_key_id, access_key_secret, endpoint, bucket_name)

        # 从 OSS 获取对象
        oss_data = fetch_files_from_oss(oss_client)

        # Add new files to database
        add_files_to_database(oss_data.get('files'))
        logger.info("Task completed")

        return oss_data

    except Exception as e:
        print(f"Task failed with exception: {str(e)}")
        logger.error(f"Task failed with exception: {str(e)}")
        return {
            'status': 'Task failed',
            'error': str(e)
        }


def fetch_files_from_oss(oss_client):
    files = []
    total = 0  # 记录总共获取了多少条数据
    marker = ''

    while True:
        result = oss_client.bucket.list_objects(prefix='images/', marker=marker, max_keys=10)

        for obj in result.object_list:
            if obj.key.endswith('.jpg') or obj.key.endswith('.png') or obj.key.endswith('.webp'):
                file_name = os.path.basename(obj.key)
                detailed_obj = oss_client.bucket.head_object(obj.key)
                content_type = detailed_obj.headers['Content-Type']
                last_modified = datetime.utcfromtimestamp(obj.last_modified)
                path = '/' + obj.key

                file_info = {
                    'name': file_name,
                    'path': path,
                    'last_modified': last_modified,
                    'size': obj.size,
                    'content_type': content_type
                }
                files.append(file_info)
                total += 1  # 每次添加一个文件信息时增加计数

        # 如果已经获取了 10 条数据，则退出循环
        # if total >= 100:
        #     break

        if result.next_marker:
            marker = result.next_marker
        else:
            break
    return {'files': files, 'total': total}


def add_files_to_database(files):
    existing_file_names = {file.name for file in Image.query.all()}
    files_to_add = []

    for file_info in files:
        if file_info['name'] not in existing_file_names:
            file_to_add = Image(
                name=file_info['name'],
                path=file_info['path'],
                last_modified=file_info['last_modified'],
                size=file_info['size'],
                content_type=file_info['content_type']
            )
            files_to_add.append(file_to_add)

    if files_to_add:
        db.session.add_all(files_to_add)
        db.session.commit()


@image_api_pb.route('/image/asyncOss')
@jwt_required()
def readImageOss():
    task = current_app.celery.send_task("fetch_images_from_oss")
    return jsonify({"code": 200, "message": "Task started", "data": {}, "task_id": task.id}), 200


@image_api_pb.route('/image/task_status/<task_id>', methods=['GET'])
@jwt_required()
def get_task_status(task_id):
    try:
        task = current_app.celery.AsyncResult(task_id)
        print(f"Task state: {task.state}")

        if task.state == 'PENDING':
            data = {
                'state': task.state,
                'total': 0,
                'status': 'Pending...'
            }
        elif task.state == 'SUCCESS':
            data = {
                'state': task.state,
                'total': task.info.get('total', 1),
                'status': 'Task completed successfully'
            }
        elif task.state == 'FAILURE':
            data = {
                'state': task.state,
                'total': 0,
                'status': 'Task failed'
            }
        else:
            data = {
                'state': task.state,
                'total': task.info.get('total', 0),
                'status': 'Task in progress...'
            }

        return jsonify({"code": 200, "message": "", "data": data}), 200

    except Exception as e:
        print(f"Error retrieving task status: {str(e)}")
        return jsonify({"code": 500, "message": "Internal Server Error", "data": {}}), 500
