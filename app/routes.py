from flask import Blueprint, jsonify

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
