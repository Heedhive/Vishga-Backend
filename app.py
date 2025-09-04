from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
from extensions import db, DATABASE_URL
from flask_migrate import Migrate

from api.products import products_bp
from api.cart import cart_bp
from api.auth import auth_bp

load_dotenv()
migrate = Migrate()
def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24)  # Simple secret key for Flask
    CORS(app, supports_credentials=True)

    # Config for file uploads
    UPLOAD_FOLDER = 'static/uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
  
    # ✅ Database setup (Postgres)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Bind db to app
    # db.init_app(app)

    # Register Blueprints
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(auth_bp)
    db.init_app(app)
    migrate.init_app(app, db)  
    return app
