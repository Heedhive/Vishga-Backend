import sys
import os

from flask import Flask
from app import create_app
from api.cart import db  # import db and Postgres URL
from extensions import DATABASE_URL
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = create_app()

# Configure DB
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Create tables in Postgres (only if they don't exist)
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
