from flask import Blueprint, jsonify, request
from model.wedding_music import WeddingMusic
from model.wedding_photo_wall import WeddingPhotoWall
from datetime import datetime
from extensions import db
from config import endpoint, bucket_name
import os
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider

wedding_api_pb = Blueprint('wedding_api', __name__)


@wedding_api_pb.route('/wedding/music/add', methods=['Post'])
def add_wedding_music():
    data = request.get_json()
    if not data:
        return jsonify({"code": 500, "message": "No input data provided"}), 200
    title = data.get('title')
    artist = data.get('artist')
    url = data.get('url')
    album = data.get('album')
    if not title or not url:
        return jsonify({"code": 500, "message": "Title and url are required"}), 200

    new_wedding_music = WeddingMusic(
        title=title,
        artist=artist,
        album=album,
        path=url,
    )
    try:
        db.session.add(new_wedding_music)
        db.session.commit()
        return jsonify({"code": 200, "message": "Music added successfully", "data": {
            "music_id": new_wedding_music.id
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e)}), 200


@wedding_api_pb.route('/wedding/music/list', methods=['GET'])
def get_music_list():
    music_records = WeddingMusic.query.all()
    playlists = [music.to_dict() for music in music_records]
    return jsonify({"code": 200, "message": "Success", "data": playlists}), 200


@wedding_api_pb.route('/wedding/photo/wall/list', methods=['GET'])
def get_wedding_photo_wall_list():
    page_number = request.args.get('pageNumber', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    keyword = request.args.get('keyword', '', type=str)

    try:
        query = WeddingPhotoWall.query.filter(WeddingPhotoWall.is_show == True).order_by(WeddingPhotoWall.order.desc(), WeddingPhotoWall.created_at.desc())
        if keyword:
            query = query.filter(WeddingPhotoWall.title.ilike(f"%{keyword}%"))

        photos = query.paginate(page=page_number, per_page=page_size, error_out=False)
        photo_list = [photo.to_dict() for photo in photos.items]  # 使用 photos.items
        total = photos.total
        return jsonify({"code": 200, "message": "Success", "data": photo_list, "total": total}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200
    

@wedding_api_pb.route('/wedding/photo/wall/list/all', methods=['GET'])
def get_wedding_photo_wall_list_all():
    keyword = request.args.get('keyword', '', type=str)

    try:
        # 初始查询，过滤掉 is_show 为 False 的数据
        query = WeddingPhotoWall.query.filter(WeddingPhotoWall.is_show == True).order_by(WeddingPhotoWall.order.desc(),
                                                                                         WeddingPhotoWall.created_at.desc())

        # 如果提供了 keyword，则进一步过滤
        if keyword:
            query = query.filter(WeddingPhotoWall.title.ilike(f"%{keyword}%"))

        # 获取所有数据，而不是分页
        photos = query.all()
        photo_list = [photo.to_dict() for photo in photos]
        total = len(photo_list)  # 更新total的计算方式
        return jsonify({"code": 200, "message": "Success", "data": photo_list, "total": total}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@wedding_api_pb.route('/wedding/photo/wall/delete', methods=['POST'])
def delete_wedding_photo():
    data = request.get_json()
    if not data:
        return jsonify({"code": 500, "message": "No input data provided"}), 200
    photo_id = data.get('id')
    if not photo_id:
        return jsonify({"code": 500, "message": "Missing ID", "data": {}}), 200
    try:
        # 查找并删除数据库记录
        photo = WeddingPhotoWall.query.get(photo_id)
        if not photo:
            return jsonify({"code": 500, "message": "Photo not found", "data": {}}), 200
        # 删除 OSS 中的图片
        src = photo.src
        if src:
            access_key_id = os.environ.get('OSS_ACCESS_KEY_ID')
            access_key_secret = os.environ.get('OSS_ACCESS_KEY_SECRET')
            print(f'Access Key ID: {access_key_id}')
            print(f'Access Key Secret: {access_key_secret}')
            auth = oss2.ProviderAuth(EnvironmentVariableCredentialsProvider())
            bucket = oss2.Bucket(auth, endpoint, bucket_name)
            bucket.delete_object(src)
        # 删除数据库记录
        db.session.delete(photo)
        db.session.commit()
        return jsonify({"code": 200, "message": "Success", "data": {}}), 200
    except Exception as e:
        db.session.rollback()  # 发生错误时回滚事务
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@wedding_api_pb.route('/wedding/photo/wall/add', methods=['POST'])
def add_wedding_photo_wall():
    data = request.get_json()
    if not data:
        return jsonify({"code": 500, "message": "No input data provided"}), 200
    title = data.get('title')
    description = data.get('description')
    src = data.get('src')
    order = data.get('order', 0)

    if not title or not src:
        return jsonify({"code": 500, "message": "Title and src are required"}), 200

    new_photo = WeddingPhotoWall(
        title=title,
        description=description,
        src=src,
        order=order,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    try:
        db.session.add(new_photo)
        db.session.commit()
        return jsonify({"code": 200, "message": "Photo added successfully", "data": {
            "id": new_photo.id,
            "title": new_photo.title,
            "description": new_photo.description,
            "src": new_photo.src,
            "created_at": new_photo.created_at,
            "updated_at": new_photo.updated_at
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e)}), 200