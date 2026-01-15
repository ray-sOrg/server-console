import uuid
from extensions import db
from datetime import datetime


class User(db.Model):
    __tablename__ = 'app_user'  # PostgreSQL: user 是保留字
    id = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(36), unique=True, nullable=False)  # UUID 字段
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'super_admin', 'admin', 'user'
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        self.generate_uid()

    def generate_uid(self):
        self.uid = str(uuid.uuid4())

    def __repr__(self):
        return f'<User {self.username}>'
