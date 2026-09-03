import sqlalchemy as db
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

# The restaurant database is separate from the console database. Keep these
# models out of Flask-SQLAlchemy's default create_all() metadata.
RestaurantBase = declarative_base()


class Dish(RestaurantBase):
    __tablename__ = 'Dish'
    
    id = db.Column(db.Uuid(as_uuid=False), primary_key=True)
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
    nutrition = relationship(
        'DishNutrition', uselist=False, back_populates='dish',
        cascade='all, delete-orphan', lazy='selectin',
    )
    
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
            'nutrition': self.nutrition.to_dict() if self.nutrition else None,
            'createdAt': self.createdAt.isoformat() if self.createdAt else None,
            'updatedAt': self.updatedAt.isoformat() if self.updatedAt else None
        }


class DishNutrition(RestaurantBase):
    __tablename__ = 'DishNutrition'

    dishId = db.Column(
        db.Uuid(as_uuid=False),
        db.ForeignKey('Dish.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True,
    )
    basis = db.Column(db.String(20), nullable=False)
    defaultServingAmount = db.Column(db.Numeric(10, 2), nullable=False)
    servingUnit = db.Column(db.String(10), nullable=False)
    caloriesKcal = db.Column(db.Numeric(10, 2), nullable=False)
    proteinG = db.Column(db.Numeric(10, 2))
    carbohydrateG = db.Column(db.Numeric(10, 2))
    fatG = db.Column(db.Numeric(10, 2))
    fiberG = db.Column(db.Numeric(10, 2))
    sugarG = db.Column(db.Numeric(10, 2))
    sodiumMg = db.Column(db.Numeric(10, 2))
    labelImageUrl = db.Column(db.Text)
    dish = relationship('Dish', back_populates='nutrition')

    def to_dict(self):
        result = {
            'basis': self.basis,
            'servingUnit': self.servingUnit,
            'labelImageUrl': self.labelImageUrl,
        }
        for field in (
            'defaultServingAmount', 'caloriesKcal', 'proteinG',
            'carbohydrateG', 'fatG', 'fiberG', 'sugarG', 'sodiumMg',
        ):
            value = getattr(self, field)
            result[field] = float(value) if value is not None else None
        return result
