from app import app, db
from sqlalchemy import inspect

with app.app_context():
    inspector = inspect(db.engine)

    print("Schema public:")
    print(inspector.get_table_names(schema="public"))

    print("\nSchema ouvirtiba:")
    print(inspector.get_table_names(schema="ouvirtiba"))