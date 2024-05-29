from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from utils.oss_utils import OSSClient
from model.image import Image
from config import access_key_id, access_key_secret, endpoint, bucket_name
from app import app
from utils.celery_utils import celery
from datetime import datetime
from extensions import db
import os

index_api_pb = Blueprint('index_api', __name__)


@index_api_pb.route('/logger')
def logger():
    app.logger.debug("FLASK_ENV: %s", os.environ.get('FLASK_ENV'))
    return "Hello, Logger!"


@index_api_pb.route('/index')
@jwt_required()
def index():
    response = {
        "code": 200,
        "message": "Success",
        "data": "index test"
    }
    return jsonify(response)


@celery.task
def fetch_images_from_oss():
    oss_client = OSSClient(access_key_id, access_key_secret, endpoint, bucket_name)
    files = []
    marker = ''

    while True:
        result = oss_client.bucket.list_objects(max_keys=1000, marker=marker)

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

        if result.next_marker:
            marker = result.next_marker
        else:
            break

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

    return files


@index_api_pb.route('/image/asyncOss')
@jwt_required()
def readImageOss():
    task = fetch_images_from_oss.delay()
    return jsonify({"code": 200, "message": "Task started", "task_id": task.id}), 202


@index_api_pb.route('/image/task_status/<task_id>')
@jwt_required()
def get_task_status(task_id):
    task = fetch_images_from_oss.AsyncResult(task_id)
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info)
        }
    return jsonify(response)
