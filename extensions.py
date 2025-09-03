from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

# Use Render PostgreSQL (set in environment variable)
DATABASE_URL = os.environ.get("DATABASE_URL") or \
    "postgresql://vishaga_db_user:sfqH9CKSp9GqZ8AT2S45kfSBKxNp86kO@dpg-d2s5pemmcj7s73ft3mb0-a.oregon-postgres.render.com/vishaga_db"