from flask import Blueprint, jsonify
from flask import request
from flask_jwt_extended import create_access_token
from .models import db, User, Plant, Progress
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity

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

from flask_jwt_extended import jwt_required, get_jwt_identity

@api.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    user_id = get_jwt_identity()
    return jsonify({"message": f"Hello user {user_id}, you are authenticated!"})

from flask_jwt_extended import jwt_required, get_jwt_identity

@api.route("/api/plants", methods=["POST"])
@jwt_required()
def add_plant():
    data = request.get_json()
    user_id = get_jwt_identity()

    new_plant = Plant(
        user_id=user_id,
        name=data["name"],
        species=data.get("species"),
        date_planted=data.get("date_planted"),
        notes=data.get("notes")
    )

    db.session.add(new_plant)
    db.session.commit()
    return jsonify({"message": "Plant added!"}), 201

@api.route("/api/plants", methods=["GET"])
@jwt_required()
def get_user_plants():
    user_id = get_jwt_identity()
    plants = Plant.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "id": plant.id,
        "name": plant.name,
        "species": plant.species,
        "date_planted": str(plant.date_planted),
        "notes": plant.notes
    } for plant in plants])
