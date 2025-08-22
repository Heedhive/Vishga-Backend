from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import uuid
import datetime

auth_bp = Blueprint('auth', __name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')

def init_db_for_users():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
        ''')
        conn.commit()

def init_db_for_tokens():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        conn.commit()

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'Missing fields'}), 400

    hashed_password = generate_password_hash(password)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                           (username, email, hashed_password))
            conn.commit()
            user_id = cursor.lastrowid
            # Generate a new token for signup
            token = str(uuid.uuid4())
            expires_at = datetime.datetime.now() + datetime.timedelta(hours=1) # Token valid for 1 hour
            cursor.execute('INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)',
                           (token, user_id, expires_at))
            conn.commit()
            return jsonify({'message': 'Signup successful', 'user_id': user_id, 'token': token}), 201
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username or email already exists'}), 409

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()

    if user and check_password_hash(user['password'], password):
        # Generate a new token
        token = str(uuid.uuid4())
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=1) # Token valid for 1 hour

        cursor.execute('INSERT INTO tokens (token, user_id, expires_at) VALUES (?, ?, ?)',
                       (token, user['id'], expires_at))
        conn.commit()

        return jsonify({'message': 'Login successful', 'token': token, 'user_id': user['id']}), 200
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

# Decorator to protect routes
def token_required(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        token = token.replace('Bearer ', '')

        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tokens WHERE token = ? AND expires_at > ?',
                           (token, datetime.datetime.now()))
            token_entry = cursor.fetchone()

        if not token_entry:
            return jsonify({'message': 'Token is invalid or expired!'}), 401

        request.user_id = token_entry['user_id'] # Attach user_id to request object
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__ # Preserve original function name
    return decorated_function

@auth_bp.route('/user_profile', methods=['GET'])
@token_required
def user_profile():
    user_id = request.user_id
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        if user:
            return jsonify({'id': user['id'], 'username': user['username'], 'email': user['email']}), 200
        else:
            return jsonify({'error': 'User not found'}), 404

@auth_bp.route('/check_login')
@token_required
def check_login():
    return jsonify({'message': 'User is logged in'}), 200

@auth_bp.route('/logout', methods=['POST'])
@token_required
def logout():
    token = request.headers.get('Authorization').replace('Bearer ', '')
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tokens WHERE token = ?', (token,))
        conn.commit()
    return jsonify({'message': 'Logout successful'}), 200


@auth_bp.route("/get_userr", methods=["GET"])
def fet_user():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, email FROM users')  # specify the table name
        users = cursor.fetchall()
        user_list = [dict(user) for user in users]  # convert each Row to dict
        return jsonify({'users': user_list}), 200

@auth_bp.route('/user_profile', methods=['PUT'])
@token_required
def update_user_profile():
    user_id = request.user_id
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email:
        return jsonify({'error': 'Missing username or email'}), 400

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        try:
            if password:
                hashed_password = generate_password_hash(password)
                cursor.execute('UPDATE users SET username = ?, email = ?, password = ? WHERE id = ?',
                               (username, email, hashed_password, user_id))
            else:
                cursor.execute('UPDATE users SET username = ?, email = ? WHERE id = ?',
                               (username, email, user_id))
            conn.commit()
            return jsonify({'message': 'Profile updated successfully'}), 200
        except sqlite3.IntegrityError:
            return jsonify({'error': 'Username or email already exists'}), 409
        except Exception as e:
            return jsonify({'error': str(e)}), 500