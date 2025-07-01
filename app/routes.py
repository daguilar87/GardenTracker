from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from datetime import datetime
from .models import db, User, Plant, UserPlant
from flask_jwt_extended.exceptions import JWTExtendedException
import requests
import os
import json

api = Blueprint("api", __name__)


@api.errorhandler(JWTExtendedException)
def handle_jwt_errors(e):
    return jsonify({"error": str(e)}), 422


# Health check
@api.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Garden Tracker API is live!"})


# Get all plants saved by user
@api.route("/user/plants", methods=["GET"])
@jwt_required()
def get_user_plants():
    user_id = get_jwt_identity()
    user_plants = UserPlant.query.filter_by(user_id=user_id).all()

    results = []
    for up in user_plants:
        plant = up.plant
        growth_days = getattr(plant, "growth_days", 0)
        date_planted = up.date_planted.strftime("%Y-%m-%d") if up.date_planted else None

        results.append({
            "id": up.id,
            "plant_id": plant.id,
            "plant_name": plant.name,
            "growth_days": growth_days,
            "date_planted": date_planted,
            "notes": up.notes,
        })

    return jsonify(results), 200


# Get static or database plants
@api.route("/plants", methods=["GET"])
def get_plants():
    plants = Plant.query.all()
    results = [{"id": p.id, "name": p.name} for p in plants]
    return jsonify(results)


# Timeline info + growth_days
@api.route("/planting-info/<plant_name>", methods=["GET"])
@jwt_required()
def planting_info(plant_name):
    zone = request.args.get("zone")
    print(f"🌱 Requested: plant={plant_name}, zone={zone}")

    try:
        file_path = os.path.join(os.path.dirname(__file__), "static", "planting_calendar.json")
        with open(file_path) as f:
            calendar = json.load(f)
    except Exception as e:
        print("❌ Error loading JSON:", e)
        return jsonify({"error": "Failed to load planting calendar"}), 500

    info = calendar.get(plant_name, {}).get(zone)
    if not info:
        return jsonify({"error": f"No timeline found for {plant_name} in zone {zone}"}), 404

    plant = Plant.query.filter_by(name=plant_name).first()
    growth_days = plant.growth_days if plant else None
    info["growth_days"] = growth_days

    return jsonify(info)


# Register
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


# Login
@api.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user.id))
    return jsonify({"token": access_token, "username": user.username})


# Test Auth
@api.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    user_id = get_jwt_identity()
    return jsonify({"message": f"Hello user {user_id}, you are authenticated!"})


#  Get logged-in user info
@api.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify({"username": user.username})


#  Add plant to user portfolio
@api.route("/user/plants", methods=["POST"])
@jwt_required()
def add_user_plant():
    data = request.get_json()
    user_id = get_jwt_identity()

    new_plant = UserPlant(
        user_id=user_id,
        plant_id=data["plant_id"],
        date_planted=datetime.strptime(data["planting_date"], "%Y-%m-%d"),
        notes=data.get("notes", "")
    )

    db.session.add(new_plant)
    db.session.commit()
    return jsonify({"message": "Plant added to your portfolio!"}), 201


#  Update user plant notes
@api.route("/user/plants/<int:user_plant_id>", methods=["PUT"])
@jwt_required()
def update_user_plant(user_plant_id):
    data = request.get_json()
    user_id = get_jwt_identity()

    plant = UserPlant.query.filter_by(id=user_plant_id, user_id=user_id).first()
    if not plant:
        return jsonify({"error": "Plant not found"}), 404

    plant.notes = data.get("notes", plant.notes)
    db.session.commit()
    return jsonify({"message": "Plant updated!"}), 200


#  Delete a plant from user portfolio
@api.route("/user/plants/<int:user_plant_id>", methods=["DELETE"])
@jwt_required()
def delete_user_plant(user_plant_id):
    user_id = get_jwt_identity()
    plant = UserPlant.query.filter_by(id=user_plant_id, user_id=user_id).first()

    if not plant:
        return jsonify({"error": "Plant not found"}), 404

    db.session.delete(plant)
    db.session.commit()
    return jsonify({"message": "Plant deleted!"}), 200


#  Update ZIP code and zone
@api.route("/update-zip", methods=["POST"])
@jwt_required()
def update_zip():
    import sys
    print("✅ Reached /update-zip", file=sys.stderr)

    data = request.get_json(silent=True)
    print("📦 Raw JSON received:", data, file=sys.stderr)

    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    zip_code = data.get("zip_code")
    if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
        return jsonify({"error": "Invalid or missing ZIP code"}), 400

    try:
        res = requests.get(f"https://phzmapi.org/{zip_code}.json", timeout=5)
        res.raise_for_status()
        zone = res.json().get("zone")
    except Exception as e:
        return jsonify({"error": "Failed to fetch zone"}), 500

    if not zone:
        return jsonify({"error": "Zone not found for ZIP"}), 404

    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    user.zip_code = zip_code
    user.zone = zone
    db.session.commit()

    return jsonify({"zone": zone})
