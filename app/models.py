from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users" 

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    zip_code = db.Column(db.String(10))
    zone = db.Column(db.String(10))

    
    user_plants = db.relationship('UserPlant', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Plant(db.Model):
    __tablename__ = "plants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(100))
    sunlight = db.Column(db.String(50))
    watering = db.Column(db.String(50))
    growth_days = db.Column(db.Integer)


class UserPlant(db.Model):
    __tablename__ = "user_plants"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)   # ✅ matches User table
    plant_id = db.Column(db.Integer, db.ForeignKey('plants.id'), nullable=False)
    nickname = db.Column(db.String(100))
    date_planted = db.Column(db.Date, default=datetime.utcnow)
    notes = db.Column(db.Text)

   
    plant = db.relationship('Plant', backref='user_instances')
