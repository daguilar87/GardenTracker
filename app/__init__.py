from .models import db
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from app.utils.sync_calendar import sync_plants_from_calendar
import os

jwt = JWTManager()

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "default-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///garden.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    jwt.init_app(app)
    db.init_app(app)

    from .routes import api
    app.register_blueprint(api, url_prefix="/api")

    with app.app_context():
        db.create_all()
        sync_plants_from_calendar()

    return app
