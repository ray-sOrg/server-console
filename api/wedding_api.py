from flask import Blueprint, jsonify, request
from model.wedding_music import WeddingMusic
from model.wedding_photo_wall import WeddingPhotoWall
from datetime import datetime
from extensions import db


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
        return jsonify({"code": 500, "message": "Title and image_path are required"}), 200

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
        query = WeddingPhotoWall.query.order_by(WeddingPhotoWall.created_at.desc())
        if keyword:
            query = query.filter(WeddingPhotoWall.title.ilike(f"%{keyword}%"))

        photos = query.paginate(page=page_number, per_page=page_size, error_out=False)
        photo_list = [
            {
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'image_path': photo.image_path,
                'created_at': photo.created_at,
                'updated_at': photo.updated_at
            }
            for photo in photos.items
        ]
        total = photos.total
        return jsonify({"code": 200, "message": "Success", "data": photo_list, "total": total}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200
    

@wedding_api_pb.route('/wedding/photo/wall/list/all', methods=['GET'])
def get_wedding_photo_wall_list_all():
    keyword = request.args.get('keyword', '', type=str)

    try:
        query = WeddingPhotoWall.query.order_by(WeddingPhotoWall.created_at.desc())
        if keyword:
            query = query.filter(WeddingPhotoWall.title.ilike(f"%{keyword}%"))

        # 获取所有数据，而不是分页
        photos = query.all()
        photo_list = [
            {
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'image_path': photo.image_path,
                'created_at': photo.created_at,
                'updated_at': photo.updated_at
            }
            for photo in photos
        ]
        total = len(photo_list)  # 更新total的计算方式
        return jsonify({"code": 200, "message": "Success", "data": photo_list, "total": total}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": str(e), "data": {}}), 200


@wedding_api_pb.route('/wedding/photo/wall/add', methods=['POST'])
def add_wedding_photo_wall():
    data = request.get_json()
    if not data:
        return jsonify({"code": 500, "message": "No input data provided"}), 200
    title = data.get('title')
    description = data.get('description')
    image_path = data.get('image_path')

    if not title or not image_path:
        return jsonify({"code": 500, "message": "Title and image_path are required"}), 200

    new_photo = WeddingPhotoWall(
        title=title,
        description=description,
        image_path=image_path,
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
            "image_path": new_photo.image_path,
            "created_at": new_photo.created_at,
            "updated_at": new_photo.updated_at
        }}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"code": 500, "message": str(e)}), 200