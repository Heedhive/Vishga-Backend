from flask import Blueprint, request, jsonify, current_app
import sqlite3
import os
from werkzeug.utils import secure_filename

products_bp = Blueprint('products', __name__)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')

def init_db_for_products():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                prize REAL NOT NULL,
                details TEXT,
                line_description TEXT, 
                benefit TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            )
        ''')
        conn.commit()

@products_bp.route('/upload', methods=['POST'])
def upload():
    name = request.form.get('name')
    prize = request.form.get('prize')
    details = request.form.get('details')
    line_description = request.form.get('lineDescription')
    benefit = request.form.get('benefit')
    images = request.files.getlist('images')

    if not (name and prize and details):
        return jsonify({'error': 'Missing fields'}), 400

    # Store product details
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO products (name, prize, details, line_description, benefit) VALUES (?, ?, ?, ?, ?)', (name, prize, details, line_description, benefit))
        product_id = cursor.lastrowid

        # Save images
        for image in images:
            if image:
                filename = secure_filename(image.filename)
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                image.save(filepath)
                cursor.execute('INSERT INTO product_images (product_id, filename) VALUES (?, ?)', (product_id, filename))

        conn.commit()

    return jsonify({'message': 'Product saved successfully'}), 200


@products_bp.route('/products', methods=['GET'])
def get_products():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row  # To access columns by name
        cursor = conn.cursor()

        # Get all products
        cursor.execute('SELECT * FROM products')
        products = cursor.fetchall()

        # Get all images
        cursor.execute('SELECT * FROM product_images')
        images = cursor.fetchall()

        # Group images by product_id
        image_map = {}
        for img in images:
            pid = img['product_id']
            filename = img['filename']
            image_url = f"/static/uploads/{filename}"
            image_map.setdefault(pid, []).append(image_url)

        # Combine products with their images
        result = []
        for product in products:
            result.append({
                'id': product['id'],
                'name': product['name'],
                'prize': product['prize'],
                'details': product['details'],
                'images': image_map.get(product['id'], [])
            })

        return jsonify(result)
    

@products_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Get image filenames before deleting
        cursor.execute('SELECT filename FROM product_images WHERE product_id = ?', (product_id,))
        images = cursor.fetchall()

        # Delete image files from disk
        for img in images:
            path = os.path.join(current_app.config['UPLOAD_FOLDER'], img[0])
            if os.path.exists(path):
                os.remove(path)

        # Delete image records
        cursor.execute('DELETE FROM product_images WHERE product_id = ?', (product_id,))
        # Delete product
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()

    return jsonify({'message': 'Product deleted successfully'})


@products_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if not product:
            return jsonify({'error': 'Product not found'}), 404

        cursor.execute('SELECT filename FROM product_images WHERE product_id = ?', (product_id,))
        images = cursor.fetchall()
        image_urls = [f"/static/uploads/{img['filename']}" for img in images]

        return jsonify({
            'id': product['id'],
            'name': product['name'],
            'prize': product['prize'],
            'details': product['details'],
            'benefit': product['benefit'],
            'line_description': product['line_description'],
            'images': image_urls
        })

@products_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    name = request.form.get('name')
    prize = request.form.get('prize')
    details = request.form.get('details')
    new_images = request.files.getlist('images')

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Update product details
        cursor.execute('UPDATE products SET name = ?, prize = ?, details = ? WHERE id = ?',
                       (name, prize, details, product_id))

        # If new images uploaded, delete old ones
        if new_images:
            cursor.execute('SELECT filename FROM product_images WHERE product_id = ?', (product_id,))
            old_images = cursor.fetchall()
            for img in old_images:
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], img[0])
                if os.path.exists(path):
                    os.remove(path)
            cursor.execute('DELETE FROM product_images WHERE product_id = ?', (product_id,))
            for image in new_images:
                filename = secure_filename(image.filename)
                path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                image.save(path)
                cursor.execute('INSERT INTO product_images (product_id, filename) VALUES (?, ?)', (product_id, filename))

        conn.commit()

    return jsonify({'message': 'Product updated successfully'})
