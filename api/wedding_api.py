from flask import Blueprint, jsonify
from model.music import Music

wedding_api_pb = Blueprint('wedding_api', __name__)


@wedding_api_pb.route('/api/wedding/music/list', methods=['GET'])
def get_playlists():
    music_records = Music.query.all()
    playlists = [music.to_dict() for music in music_records]
    return jsonify({"code": 200, "message": "Success", "data": playlists}), 200
