from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import uuid

from api.cart import db  # reuse same SQLAlchemy instance

auth_bp = Blueprint("auth", __name__)


# ---- Models ----
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    tokens = db.relationship("Token", backref="user", cascade="all, delete-orphan")


class Token(db.Model):
    __tablename__ = "tokens"

    token = db.Column(db.String(255), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)


# ---- Routes ----

@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    phone_number = data.get("phone_number")
    address = data.get("address")

    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed_password = generate_password_hash(password)

    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return jsonify({"error": "Username or email already exists"}), 409

    user = User(
        username=username,
        email=email,
        password=hashed_password,
        phone_number=phone_number,
        address=address
    )
    db.session.add(user)
    db.session.commit()

    token_str = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(hours=1)
    token = Token(token=token_str, user_id=user.id, expires_at=expires_at)
    db.session.add(token)
    db.session.commit()

    return jsonify({
        "message": "Signup successful",
        "user_id": user.id,
        "token": token_str
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, password):
        token_str = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=1)
        token = Token(token=token_str, user_id=user.id, expires_at=expires_at)
        db.session.add(token)
        db.session.commit()
        return jsonify({"message": "Login successful", "token": token_str, "user_id": user.id}), 200

    return jsonify({"error": "Invalid credentials"}), 401


# ---- Decorator ----
def token_required(f):
    from functools import wraps

    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_str = request.headers.get("Authorization")
        if not token_str:
            return jsonify({"message": "Token is missing!"}), 401

        token_str = token_str.replace("Bearer ", "")
        token = Token.query.filter(Token.token == token_str, Token.expires_at > datetime.now()).first()

        if not token:
            return jsonify({"message": "Token is invalid or expired!"}), 401

        request.user_id = token.user_id
        return f(*args, **kwargs)

    return decorated_function


@auth_bp.route("/user_profile", methods=["GET"])
@token_required
def user_profile():
    user = User.query.get(request.user_id)
    if user:
        return jsonify({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "phone_number": user.phone_number,
            "address": user.address
        }), 200
    return jsonify({"error": "User not found"}), 404


@auth_bp.route("/check_login", methods=["GET"])
@token_required
def check_login():
    return jsonify({"message": "User is logged in"}), 200


@auth_bp.route("/logout", methods=["POST"])
@token_required
def logout():
    token_str = request.headers.get("Authorization").replace("Bearer ", "")
    token = Token.query.filter_by(token=token_str).first()
    if token:
        db.session.delete(token)
        db.session.commit()
    return jsonify({"message": "Logout successful"}), 200


@auth_bp.route("/get_users", methods=["GET"])
def get_users():
    users = User.query.all()
    return jsonify(
        {"users": [{"id": u.id, "username": u.username, "email": u.email} for u in users]}
    ), 200


@auth_bp.route("/user_profile", methods=["PUT"])
@token_required
def update_user_profile():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email:
        return jsonify({"error": "Missing username or email"}), 400

    user = User.query.get(request.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check for conflicts
    conflict = User.query.filter(
        ((User.username == username) | (User.email == email)) & (User.id != user.id)
    ).first()
    if conflict:
        return jsonify({"error": "Username or email already exists"}), 409

    user.username = username
    user.email = email
    if password:
        user.password = generate_password_hash(password)

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"}), 200
