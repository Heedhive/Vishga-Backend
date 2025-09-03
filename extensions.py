from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

# Use Render PostgreSQL (set in environment variable)
DATABASE_URL = os.environ.get("DATABASE_URL") or \
    "postgresql://db_rkrd_user:PzXukWQG6RGhyV9AwmjJfjpVdL9S44cg@dpg-d2km82bipnbc73f9gcg0-a.oregon-postgres.render.com/db_rkrd"