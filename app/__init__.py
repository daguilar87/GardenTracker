from .models import db
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate   
from dotenv import load_dotenv
import os

jwt = JWTManager()
migrate = Migrate() 

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "default-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")  # <-- use Neon
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    jwt.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)

    from .routes import api
    app.register_blueprint(api, url_prefix="/api")

    return app
