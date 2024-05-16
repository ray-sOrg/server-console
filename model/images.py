from extensions import db
from datetime import datetime


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)
    path = db.Column(db.String(200))
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
