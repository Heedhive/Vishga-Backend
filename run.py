import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from api.cart import init_db_for_cart
from api.auth import init_db_for_users, init_db_for_tokens
from api.products import init_db_for_products
from api.cart import init_db_for_orders_history

app = create_app()
init_db_for_users()
init_db_for_cart()
init_db_for_tokens()
init_db_for_products()
init_db_for_orders_history()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
