from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
import os
import io

from extensions import db  # reuse same SQLAlchemy instance
from models.product import Product, ProductImage 

products_bp = Blueprint('products', __name__)


# ---- Routes ----

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

    product = Product(
        name=name,
        prize=float(prize),
        details=details,
        line_description=line_description,
        benefit=benefit
    )
    db.session.add(product)
    db.session.commit()

    for image in images:
        if image:
            img_data = image.read()  # read file as binary
            mimetype = image.mimetype
            img = ProductImage(product_id=product.id, image_data=img_data, mimetype=mimetype)
            db.session.add(img)

    db.session.commit()

    return jsonify({'message': 'Product saved successfully'}), 201


@products_bp.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()

    result = []
    for product in products:
        image_urls = [f"/product_images/{img.id}" for img in product.images]
        result.append({
            'id': product.id,
            'name': product.name,
            'prize': product.prize,
            'details': product.details,
            'images': image_urls
        })

    return jsonify(result), 200


@products_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404  

    db.session.delete(product)
    db.session.commit()

    return jsonify({'message': 'Product deleted successfully'}), 200


@products_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Product not found'}), 404

    image_urls = [f"/product_images/{img.id}" for img in product.images]

    return jsonify({
        'id': product.id,
        'name': product.name,
        'prize': product.prize,
        'details': product.details,
        'benefit': product.benefit,
        'line_description': product.line_description,
        'images': image_urls
    }), 200


@products_bp.route("/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    name = request.form.get("name")
    prize = request.form.get("prize")
    details = request.form.get("details")
    new_images = request.files.getlist("images")

    # Update product details
    if name:
        product.name = name
    if prize:
        product.prize = float(prize)
    if details:
        product.details = details

    # Replace images if new ones uploaded
    if new_images:
        # Delete old images from DB
        ProductImage.query.filter_by(product_id=product.id).delete()

        # Add new images
        for image in new_images:
            img_data = image.read()
            mimetype = image.mimetype
            new_img = ProductImage(product_id=product.id, image_data=img_data, mimetype=mimetype)
            db.session.add(new_img)

    db.session.commit()
    return jsonify({"message": "Product updated successfully"}), 200

@products_bp.route("/product_images/<int:image_id>", methods=["GET"])
def get_product_image(image_id):
    img = ProductImage.query.get(image_id)
    if not img:
        return jsonify({"error": "Image not found"}), 404

    return send_file(io.BytesIO(img.image_data), mimetype=img.mimetype)