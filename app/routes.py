from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)
from datetime import datetime
from .models import db, User, Plant, UserPlant
import requests
from json import JSONEncoder
from flask_jwt_extended.exceptions import JWTExtendedException
from flask import jsonify
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

# Static sample plants — can remove once you use a real DB or external API
plants = [
    {'id': 1, 'name': 'Tomato', 'datePlanted': '2025-05-01', 'growthStage': 'Seedling'},
    {'id': 2, 'name': 'Basil', 'datePlanted': '2025-05-15', 'growthStage': 'Vegetative'},
    {'id': 3, 'name': 'Carrot', 'datePlanted': '2025-06-01', 'growthStage': 'Germination'},
]

@api.route("/plants", methods=["GET"])
def get_plants():
    return jsonify(plants)

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

    # Convert user.id to string here:
    access_token = create_access_token(identity=str(user.id))
    return jsonify({"token": access_token, "username": user.username})


# Auth test
@api.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    user_id = get_jwt_identity()
    return jsonify({"message": f"Hello user {user_id}, you are authenticated!"})

# Get current logged-in user info
@api.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    return jsonify({"username": user.username})

# Add a plant to user portfolio
@api.route("/user/plants", methods=["POST"])
@jwt_required()
def add_user_plant():
    data = request.get_json()
    user_id = get_jwt_identity()

    new_plant = UserPlant(
        user_id=user_id,
        plant_id=data["plant_id"],
        planting_date=datetime.strptime(data["planting_date"], "%Y-%m-%d"),
        notes=data.get("notes", "")
    )

    db.session.add(new_plant)
    db.session.commit()
    return jsonify({"message": "Plant added to your portfolio!"}), 201

# Get all plants saved by user
@api.route("/user/plants", methods=["GET"])
@jwt_required()
def get_user_plants():
    user_id = get_jwt_identity()
    user_plants = UserPlant.query.filter_by(user_id=user_id).all()

    results = []
    for up in user_plants:
        results.append({
            "id": up.id,
            "plant_name": up.plant.name,
            "planting_date": up.planting_date.strftime("%Y-%m-%d"),
            "notes": up.notes
        })

    return jsonify(results), 200

# Update user plant notes
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

# Delete a plant from user portfolio
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

@api.route("/update-zip", methods=["POST"])
@jwt_required()
def update_zip():
    import sys
    print("✅ Reached /update-zip", file=sys.stderr)

    # Attempt to parse JSON safely
    data = request.get_json(silent=True)
    print("📦 Raw JSON received:", data, file=sys.stderr)

    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    zip_code = data.get("zip_code")
    print("📬 ZIP received:", zip_code, file=sys.stderr)

    if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
        print("🚫 Invalid ZIP code:", zip_code, file=sys.stderr)
        return jsonify({"error": "Invalid or missing ZIP code"}), 400

    try:
        res = requests.get(f"https://phzmapi.org/{zip_code}.json", timeout=5)
        res.raise_for_status()
        zone = res.json().get("zone")
        print("🌎 Zone fetched:", zone, file=sys.stderr)
    except Exception as e:
        print("❌ Zone API failed:", e, file=sys.stderr)
        return jsonify({"error": "Failed to fetch zone"}), 500

    if not zone:
        return jsonify({"error": "Zone not found for ZIP"}), 404

    # Save to DB
    from .models import User
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    user.zip_code = zip_code
    user.zone = zone
    db.session.commit()

    print("✅ Zone saved successfully", file=sys.stderr)
    return jsonify({"zone": zone})


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

    return jsonify(info)

