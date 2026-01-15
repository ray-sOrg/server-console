from extensions import db
from datetime import datetime


class WeddingPhotoWall(db.Model):
    __tablename__ = 'wedding_photo_wall'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    src = db.Column(db.String(255), nullable=False)
    order = db.Column(db.Integer, nullable=True)
    is_show = db.Column(db.Boolean, default=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f'<PhotoWall id={self.id} title={self.title} created_at={self.created_at}>'

    def __init__(self, title, description, src, order, is_show, created_at, updated_at):
        self.title = title
        self.description = description
        self.src = src
        self.order = order
        self.is_show = is_show
        self.created_at = created_at
        self.updated_at = updated_at

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'src': self.src,
            'is_show': self.is_show,
            'order': self.order,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

