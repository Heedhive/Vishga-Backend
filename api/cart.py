from flask import Blueprint, request, jsonify, current_app
import sqlite3
import os
import datetime
import razorpay

cart_bp = Blueprint('cart', __name__)

razorpay_client = razorpay.Client(
    auth=(os.environ.get('RAZORPAY_KEY_ID'), os.environ.get('RAZORPAY_KEY_SECRET'))
)

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database.db')

def init_db_for_cart():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cart (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                productId INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (productId) REFERENCES products(id)
            )
        ''')
        conn.commit()

def init_db_for_orders_history():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price_at_purchase REAL NOT NULL,
                purchase_date DATETIME NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        conn.commit()

@cart_bp.route('/cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    user_id = data.get('userId')
    productId = data.get('productId')
    product_name = data.get('productName')
    quantity = data.get('quantity')

    if not user_id or not productId or not product_name or not quantity:
        return jsonify({'error': 'Missing fields'}), 400

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO cart (user_id, productId, product_name, quantity) VALUES (?, ?, ?, ?)',
                       (user_id, productId, product_name, quantity))
        conn.commit()
        return jsonify({'message': 'Item added to cart successfully'}), 201

@cart_bp.route('/cart/<int:user_id>', methods=['GET'])
def get_user_cart(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cart WHERE user_id = ?', (user_id,))
        cart_items = cursor.fetchall()
        return jsonify([dict(item) for item in cart_items]), 200

@cart_bp.route('/orders_history', methods=['GET'])
def get_all_orders_history():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders_history ORDER BY purchase_date DESC')
        all_orders = cursor.fetchall()
        return jsonify([dict(order) for order in all_orders]), 200

@cart_bp.route('/cart/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cart WHERE id = ?', (item_id,))
        conn.commit()
        return jsonify({'message': 'Item removed from cart successfully'}), 200

@cart_bp.route('/cart/<int:item_id>', methods=['PUT'])
def update_cart_item_quantity(item_id):
    data = request.get_json()
    quantity = data.get('quantity')

    if quantity is None or not isinstance(quantity, int) or quantity < 1:
        return jsonify({'error': 'Quantity must be a positive integer'}), 400

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE cart SET quantity = ? WHERE id = ?',
                       (quantity, item_id))
        conn.commit()
        if cursor.rowcount == 0:
            return jsonify({'message': 'Cart item not found'}), 404
        return jsonify({'message': 'Cart item quantity updated successfully'}), 200

@cart_bp.route('/cart/checkout', methods=['POST'])
def checkout_cart():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cart WHERE user_id = ?', (user_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            return jsonify({'message': 'Cart is empty'}), 400

        total_amount = 0
        for item in cart_items:
            cursor.execute('SELECT prize FROM products WHERE id = ?', (item[2],))
            product_price = cursor.fetchone()
            if product_price:
                total_amount += product_price[0] * item[4]

        order_amount = int(total_amount * 100)

        order_data = {
            'amount': order_amount,
            'currency': 'INR',
            'receipt': f'order_rcptid_{user_id}_{datetime.datetime.now().timestamp()}'
        }
        razorpay_order = razorpay_client.order.create(order_data)

    return jsonify({
        'message': 'Checkout successful',
        'order_id': razorpay_order['id'],
        'razorpay_key': os.environ.get('RAZORPAY_KEY_ID'),
        'amount': razorpay_order['amount'],
        'currency': razorpay_order['currency']
    }), 200

@cart_bp.route('/cart/buy_item/<int:item_id>', methods=['POST'])
def buy_single_item(item_id):
    data = request.get_json()
    amount = data.get('amount')
    currency = data.get('currency')

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cart WHERE id = ?', (item_id,))
        item = cursor.fetchone()

        if not item:
            return jsonify({'message': 'Cart item not found'}), 404

        order_amount = int(amount * 100)

        order_data = {
            'amount': order_amount,
            'currency': currency,
            'receipt': f'order_rcptid_{item["user_id"]}_{datetime.datetime.now().timestamp()}'
        }
        razorpay_order = razorpay_client.order.create(order_data)

    return jsonify({
        'message': 'Checkout successful',
        'order_id': razorpay_order['id'],
        'razorpay_key': os.environ.get('RAZORPAY_KEY_ID'),
        'amount': razorpay_order['amount'],
        'currency': razorpay_order['currency']
    }), 200

@cart_bp.route('/orders_history/<int:user_id>', methods=['GET'])
def get_user_orders_history(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders_history WHERE user_id = ? ORDER BY purchase_date DESC', (user_id,))
        order_items = cursor.fetchall()
        return jsonify([dict(item) for item in order_items]), 200

@cart_bp.route('/cart/verify_payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError as e:
        return jsonify({'error': 'Invalid payment signature'}), 400

    # Payment is successful, now move items from cart to order history
    # You might want to get user_id from the session or token
    # For now, I'll assume it's passed in the request
    user_id = 1 # Replace with actual user_id from session or token

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM cart WHERE user_id = ?', (user_id,))
        cart_items = cursor.fetchall()

        if not cart_items:
            return jsonify({'message': 'Cart is empty'}), 400

        for item in cart_items:
            cursor.execute('SELECT prize FROM products WHERE id = ?', (item[2],))
            product_price = cursor.fetchone()
            if product_price:
                cursor.execute('INSERT INTO orders_history (user_id, product_id, product_name, quantity, price_at_purchase, purchase_date) VALUES (?, ?, ?, ?, ?, ?)',
                               (user_id, item[2], item[3], item[4], product_price[0], datetime.datetime.now()))
                cursor.execute('DELETE FROM cart WHERE id = ?', (item[0],))
        conn.commit()

    return jsonify({'message': 'Payment successful and order placed'}), 200