from extensions import db
from datetime import datetime


class Dish(db.Model):
    __tablename__ = 'Dish'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.Text, nullable=False)
    nameEn = db.Column(db.Text)
    description = db.Column(db.String(500))
    descEn = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    image = db.Column(db.Text)
    category = db.Column(db.String(20))  # APPETIZER, MAIN_COURSE, etc.
    isSpicy = db.Column(db.Boolean, default=False)
    isVegetarian = db.Column(db.Boolean, default=False)
    isAvailable = db.Column(db.Boolean, default=True)
    createdAt = db.Column(db.DateTime, default=datetime.utcnow)
    updatedAt = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'nameEn': self.nameEn,
            'description': self.description,
            'descEn': self.descEn,
            'price': float(self.price) if self.price else 0,
            'image': self.image,
            'category': self.category,
            'isSpicy': self.isSpicy,
            'isVegetarian': self.isVegetarian,
            'isAvailable': self.isAvailable,
            'createdAt': self.createdAt.isoformat() if self.createdAt else None,
            'updatedAt': self.updatedAt.isoformat() if self.updatedAt else None
        }
