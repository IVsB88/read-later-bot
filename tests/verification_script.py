# verify_db.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_dir.models import Base
from database.db_handler import DatabaseHandler
from sqlalchemy import inspect

def verify_schema():
    db = DatabaseHandler()
    inspector = inspect(db.engine)
    
    for table in inspector.get_table_names():
        print(f"\nTable: {table}")
        print("Columns:")
        for column in inspector.get_columns(table):
            print(f"  - {column['name']}: {column['type']} (nullable: {column['nullable']})")
        print("Foreign Keys:")
        for fk in inspector.get_foreign_keys(table):
            print(f"  - {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

if __name__ == "__main__":
    verify_schema()