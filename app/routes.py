from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity
)
from flask_jwt_extended.exceptions import JWTExtendedException
from datetime import datetime, timedelta
from .models import db, User, Plant, UserPlant
import requests
import os
import json

api = Blueprint("api", __name__)

# Refresh access token using refresh token
@api.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    new_token = create_access_token(identity=identity)
    return jsonify(access_token=new_token), 200


@api.errorhandler(JWTExtendedException)
def handle_jwt_errors(e):
    return jsonify({"error": str(e)}), 422


@api.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Garden Tracker API is live!"})


# Get all user plants
@api.route("/user/plants", methods=["GET"])
@jwt_required()
def get_user_plants():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    zone = user.zone.lower() if user.zone else None

    
    try:
        file_path = os.path.join(os.path.dirname(__file__), "static", "planting_calendar.json")
        with open(file_path) as f:
            calendar = json.load(f)
    except Exception:
        calendar = {}

    user_plants = UserPlant.query.filter_by(user_id=user_id).join(Plant).order_by(UserPlant.date_planted.asc()).all()

    results = []
    for up in user_plants:
        plant = up.plant
        name = plant.name

        
        growth_days = plant.growth_days or calendar.get(name, {}).get("average_days_to_harvest")

        raw_zone_info = calendar.get(name, {}).get(zone, {})
        timeline = {
            "start_month": raw_zone_info.get("start"),
            "end_month": raw_zone_info.get("end")
        }

        days_remaining = None
        expected_harvest = None
        if up.date_planted and growth_days:
            days_since_planting = (datetime.utcnow().date() - up.date_planted).days
            days_remaining = growth_days - days_since_planting
            expected_harvest = (up.date_planted + timedelta(days=growth_days)).strftime("%Y-%m-%d")

        results.append({
            "id": up.id,
            "plant_name": name,
            "nickname": up.nickname,
            "growth_days": growth_days,
            "date_planted": up.date_planted.strftime("%Y-%m-%d") if up.date_planted else None,
            "notes": up.notes,
            "timeline": timeline,
            "days_remaining": days_remaining,
            "expected_harvest": expected_harvest
        })

    return jsonify(results), 200



# Add plant to user garden 
@api.route("/user/plants", methods=["POST"])
@jwt_required()
def add_user_plant():
    data = request.get_json()
    user_id = get_jwt_identity()

    planting_date = data.get("planting_date")
    notes = data.get("notes", "")
    plant_id = data.get("plant_id")
    plant_name = data.get("plant_name")

    if not planting_date or (not plant_id and not plant_name):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        planting_date_obj = datetime.strptime(planting_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400

    if plant_id:
        plant = Plant.query.get(plant_id)
        if not plant:
            return jsonify({"error": "Plant not found"}), 404
        name = plant.name
    else:
        name = plant_name.strip().title()
        plant = Plant.query.filter_by(name=name).first()
        if not plant:
            plant = Plant(name=name)
            db.session.add(plant)
            db.session.commit()

    existing = UserPlant.query.filter_by(user_id=user_id).join(Plant).filter(Plant.name == name).all()
    if existing:
        nickname = f"{name} (Batch {len(existing)+1})"
    else:
        nickname = name

    new_user_plant = UserPlant(
        user_id=user_id,
        plant_id=plant.id,
        nickname=nickname,
        date_planted=planting_date_obj,
        notes=notes
    )

    db.session.add(new_user_plant)
    db.session.commit()

    
    response = {
        "id": new_user_plant.id,
        "plant_name": name,
        "nickname": nickname,
        "date_planted": planting_date,
        "notes": notes,
        "growth_days": plant.growth_days,
        "expected_harvest": (planting_date_obj + timedelta(days=plant.growth_days)).strftime("%Y-%m-%d") if plant.growth_days else None,
    }

    return jsonify(response), 201




# Get all available plants from DB
@api.route("/plants", methods=["GET"])
def get_plants():
    plants = Plant.query.all()
    return jsonify([{"id": p.id, "name": p.name} for p in plants])


# Get planting timeline and growth days if available
@api.route("/planting-info/<plant_name>", methods=["GET"])
@jwt_required()
def planting_info(plant_name):
    zone = request.args.get("zone")
    if not zone:
        return jsonify({"error": "Zone not provided"}), 400

    plant_name = plant_name.strip().title()
    zone = zone.strip().lower()

   
    try:
        file_path = os.path.join(os.path.dirname(__file__), "static", "planting_calendar.json")
        with open(file_path) as f:
            calendar = json.load(f)
    except Exception:
        return jsonify({"error": "Failed to load planting calendar"}), 500

    plant_data = calendar.get(plant_name)
    if not plant_data:
        return jsonify({"error": f"No data found for {plant_name}"}), 404

   
    zone_match = None
    for z in plant_data.keys():
        if z.lower() == zone:
            zone_match = z
            break
    
    if not zone_match:
        zone_match = next(iter(plant_data.keys()), None)
        if not zone_match:
            return jsonify({"error": f"No timeline found for {plant_name}"}), 404

    info = plant_data[zone_match]

   
    plant = Plant.query.filter_by(name=plant_name).first()
    growth_days = plant.growth_days if plant else None

    response = {
        "zones": { zone_match: { "start_month": info.get("start"), "end_month": info.get("end") } },
        "average_days_to_harvest": growth_days
    }

    return jsonify(response)





# Update ZIP code and zone
@api.route("/update-zip", methods=["POST"])
@jwt_required()
def update_zip():
    data = request.get_json()
    zip_code = data.get("zip_code")

    if not zip_code or not zip_code.isdigit() or len(zip_code) != 5:
        return jsonify({"error": "Invalid ZIP code"}), 400

    try:
        res = requests.get(f"https://phzmapi.org/{zip_code}.json", timeout=5)
        res.raise_for_status()
        zone = res.json().get("zone")
    except:
        return jsonify({"error": "Failed to fetch zone"}), 500

    user = User.query.get(get_jwt_identity())
    user.zip_code = zip_code
    user.zone = zone
    db.session.commit()

    return jsonify({"zone": zone})


# Auth: Register
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


# Auth: Login - returns access + refresh tokens
@api.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "token": access_token,
        "refresh_token": refresh_token,
        "username": user.username
    })


# Get current user info
@api.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user = User.query.get(get_jwt_identity())
    return jsonify({
        "username": user.username,
        "zone": user.zone,
        "zip_code": user.zip_code
    })


# Update a user plant (plant, notes, or date)
@api.route("/user/plants/<int:user_plant_id>", methods=["PUT"])
@jwt_required()
def update_user_plant(user_plant_id):
    data = request.get_json()
    user_id = get_jwt_identity()

    plant_record = UserPlant.query.filter_by(id=user_plant_id, user_id=user_id).first()
    if not plant_record:
        return jsonify({"error": "Plant not found"}), 404

    if "notes" in data:
        plant_record.notes = data["notes"]
    if "date_planted" in data:
        try:
            plant_record.date_planted = datetime.strptime(data["date_planted"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Invalid date format"}), 400
    if "plant_name" in data:
        name = data["plant_name"].strip().title()
        plant = Plant.query.filter_by(name=name).first()
        if not plant:
            plant = Plant(name=name)
            db.session.add(plant)
            db.session.flush()
        plant_record.plant_id = plant.id

    db.session.commit()
    return jsonify({"message": "Plant updated!"})


# Delete user plant
@api.route("/user/plants/<int:user_plant_id>", methods=["DELETE"])
@jwt_required()
def delete_user_plant(user_plant_id):
    user_id = get_jwt_identity()
    plant = UserPlant.query.filter_by(id=user_plant_id, user_id=user_id).first()
    if not plant:
        return jsonify({"error": "Plant not found"}), 404

    db.session.delete(plant)
    db.session.commit()
    return jsonify({"message": "Plant deleted!"})
