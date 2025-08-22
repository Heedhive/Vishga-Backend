from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv

load_dotenv()

from api.products import products_bp
from api.cart import cart_bp # Updated import
from api.auth import auth_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = os.urandom(24) # A simple secret key for Flask
    CORS(app, supports_credentials=True)

    # Config for file uploads
    UPLOAD_FOLDER = 'static/uploads'
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # DB setup
    DB_PATH = os.path.join(os.path.dirname(__file__), 'database.db')
    app.config['DB_PATH'] = DB_PATH

    # Register Blueprints
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp) # Updated registration
    app.register_blueprint(auth_bp)

    return app