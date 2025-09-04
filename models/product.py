from extensions import db

# ---- Models ----
class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    prize = db.Column(db.Float, nullable=False)
    details = db.Column(db.Text)
    line_description = db.Column(db.Text)
    benefit = db.Column(db.Text)

    images = db.relationship("ProductImage", backref="product", cascade="all, delete-orphan")


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_data = db.Column(db.LargeBinary, nullable=False)   # store actual image binary
    mimetype = db.Column(db.String(50))  # e.g. "image/jpeg", "image/png"