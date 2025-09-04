from flask import Blueprint, request, jsonify
import os
import datetime
import razorpay
from extensions import db
from api.products import Product

# ---- Config ----
cart_bp = Blueprint('cart', __name__)
# db = SQLAlchemy()

razorpay_client = razorpay.Client(
    auth=(os.environ.get('RAZORPAY_KEY_ID'), os.environ.get('RAZORPAY_KEY_SECRET'))
)

# ---- Models ----
class Cart(db.Model):
    __tablename__ = "cart"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

class OrdersHistory(db.Model):
    __tablename__ = "orders_history"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    product_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_purchase = db.Column(db.Float, nullable=False)
    purchase_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)


# ---- Routes ----
@cart_bp.route('/cart', methods=['POST'])
def add_to_cart():
    data = request.get_json()
    user_id = data.get('userId')
    product_id = data.get('productId')
    product_name = data.get('productName')
    quantity = data.get('quantity')

    if not user_id or not product_id or not product_name or not quantity:
        return jsonify({'error': 'Missing fields'}), 400

    item = Cart(user_id=user_id, product_id=product_id, product_name=product_name, quantity=quantity)
    db.session.add(item)
    db.session.commit()

    return jsonify({'message': 'Item added to cart successfully'}), 201

@cart_bp.route('/cart/<int:user_id>', methods=['GET'])
def get_user_cart(user_id):
    items = Cart.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "id": i.id,
        "user_id": i.user_id,
        "product_id": i.product_id,
        "product_name": i.product_name,
        "quantity": i.quantity
    } for i in items]), 200

@cart_bp.route('/orders_history', methods=['GET'])
def get_all_orders_history():
    orders = OrdersHistory.query.order_by(OrdersHistory.purchase_date.desc()).all()
    return jsonify([{
        "id": o.id,
        "user_id": o.user_id,
        "product_id": o.product_id,
        "product_name": o.product_name,
        "quantity": o.quantity,
        "price_at_purchase": o.price_at_purchase,
        "purchase_date": o.purchase_date.isoformat()
    } for o in orders]), 200

@cart_bp.route('/cart/<int:item_id>', methods=['DELETE'])
def remove_from_cart(item_id):
    item = Cart.query.get(item_id)
    if not item:
        return jsonify({'message': 'Cart item not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'message': 'Item removed from cart successfully'}), 200

@cart_bp.route('/cart/<int:item_id>', methods=['PUT'])
def update_cart_item_quantity(item_id):
    data = request.get_json()
    quantity = data.get('quantity')

    if not quantity or not isinstance(quantity, int) or quantity < 1:
        return jsonify({'error': 'Quantity must be positive integer'}), 400

    item = Cart.query.get(item_id)
    if not item:
        return jsonify({'message': 'Cart item not found'}), 404

    item.quantity = quantity
    db.session.commit()
    return jsonify({'message': 'Cart item quantity updated successfully'}), 200

# ---- Checkout APIs ----
@cart_bp.route('/cart/checkout', methods=['POST'])
def checkout_cart():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    cart_items = Cart.query.filter_by(user_id=user_id).all()
    if not cart_items:
        return jsonify({'message': 'Cart is empty'}), 400

    total_amount = 0
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            total_amount += product.prize * item.quantity

    order_amount = int(total_amount * 100)  # Razorpay expects paise

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
    currency = data.get('currency', 'INR')

    item = Cart.query.get(item_id)
    if not item:
        return jsonify({'message': 'Cart item not found'}), 404

    order_amount = int(amount * 100)

    order_data = {
        'amount': order_amount,
        'currency': currency,
        'receipt': f'order_rcptid_{item.user_id}_{datetime.datetime.now().timestamp()}'
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
    orders = OrdersHistory.query.filter_by(user_id=user_id).order_by(OrdersHistory.purchase_date.desc()).all()
    return jsonify([{
        "id": o.id,
        "user_id": o.user_id,
        "product_id": o.product_id,
        "product_name": o.product_name,
        "quantity": o.quantity,
        "price_at_purchase": o.price_at_purchase,
        "purchase_date": o.purchase_date.isoformat()
    } for o in orders]), 200


@cart_bp.route('/cart/verify_payment', methods=['POST'])
def verify_payment():
    data = request.get_json()
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_signature = data.get('razorpay_signature')
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        razorpay_client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        return jsonify({'error': 'Invalid payment signature'}), 400

    # Move items from cart to orders_history
    cart_items = Cart.query.filter_by(user_id=user_id).all()
    if not cart_items:
        return jsonify({'message': 'Cart is empty'}), 400

    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            new_order = OrdersHistory(
                user_id=user_id,
                product_id=item.product_id,
                product_name=item.product_name,
                quantity=item.quantity,
                price_at_purchase=product.prize,
                purchase_date=datetime.datetime.utcnow()
            )
            db.session.add(new_order)
            db.session.delete(item)

    db.session.commit()

    return jsonify({'message': 'Payment successful and order placed'}), 200
