from flask import Blueprint, jsonify
from flask import request
from flask_jwt_extended import create_access_token
from .models import db, User

api = Blueprint("api", __name__)

@api.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Garden Tracker API is live!"})

# for now until i find a api or build database
plants = [
    {'id': 1, 'name': 'Tomato', 'datePlanted': '2025-05-01', 'growthStage': 'Seedling'},
    {'id': 2, 'name': 'Basil', 'datePlanted': '2025-05-15', 'growthStage': 'Vegetative'},
    {'id': 3, 'name': 'Carrot', 'datePlanted': '2025-06-01', 'growthStage': 'Germination'},
]

@api.route("/plants", methods=["GET"])
def get_plants():
    return jsonify(plants)

@api.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 400

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "User registered successfully"})

@api.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=user.id)
    return jsonify({"token": access_token, "username": user.username})