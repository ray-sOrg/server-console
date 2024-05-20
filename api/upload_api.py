from flask import Blueprint, request
from werkzeug.utils import secure_filename
import os
from extensions import db
from model.images import Image
from flask_jwt_extended import jwt_required

upload_api_pb = Blueprint('upload_api', __name__)


@upload_api_pb.route('/upload/images', methods=["POST"])
@jwt_required()
def upload_images():
    if 'file' not in request.files:
        return 'No file part'
    file = request.files['file']
    if file.filename == '':
        return 'No selected file'
    if file:
        filename = secure_filename(file.filename)
        filesave = os.path.join('static/images', filename)
        file.save(filesave)
        # Save image info to database
        new_image = Image(name=filename, path=filesave)
        db.session.add(new_image)
        db.session.commit()
        return 'File uploaded successfully'
