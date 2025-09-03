from sqlalchemy import create_engine, text

# Your PostgreSQL URL
db_url = "postgresql://db_rkrd_user:PzXukWQG6RGhyV9AwmjJfjpVdL9S44cg@dpg-d2km82bipnbc73f9gcg0-a.oregon-postgres.render.com/db_rkrd"

# Create the SQLAlchemy engine
engine = create_engine(db_url)

# Connect and run
with engine.connect() as conn:
    # Fetch all table names in the 'public' schema
    result = conn.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE';
    """))

    tables = [row[0] for row in result]

    print(f"Found tables: {tables}")

    # Drop each table using CASCADE (to handle FKs)
    for table in tables:
        print(f"Dropping table: {table}")
        conn.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE;'))

print("✅ All tables dropped successfully.")
