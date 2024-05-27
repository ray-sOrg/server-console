from extensions import db
from datetime import datetime


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    path = db.Column(db.String(200))
    upload_time = db.Column(db.DateTime, default=datetime.now)
    last_modified = db.Column(db.DateTime)
    size = db.Column(db.Integer)
    content_type = db.Column(db.String(100))

    def __init__(self, name, path, last_modified, size, content_type):
        self.name = name
        self.path = path
        self.last_modified = last_modified
        self.size = size
        self.content_type = content_type

    def __repr__(self):
        return f"Image(name='{self.name}', path='{self.path}', last_modified='{self.last_modified}', size='{self.size}', content_type='{self.content_type}')"
