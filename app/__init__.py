from .models import db
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
import os
from flask_jwt_extended import JWTManager

jwt = JWTManager()

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "default-secret")
    jwt.init_app(app)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///garden.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    JWTManager(app)
    db.init_app(app)

    from .routes import api
    app.register_blueprint(api, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app
