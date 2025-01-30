# verification_script.py
from sqlalchemy import inspect
from models_dir.models import Base
from database.db_handler import DatabaseHandler

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

# Add to verify_db.py
def check_data():
    db = DatabaseHandler()
    session = db.get_session()
    try:
        link_count = session.query(Link).count()
        reminder_count = session.query(Reminder).count()
        print(f"\nCurrent data:\nLinks: {link_count}\nReminders: {reminder_count}")
        
        # Check last reminder
        last_reminder = session.query(Reminder).order_by(Reminder.id.desc()).first()
        if last_reminder:
            print(f"\nLast reminder:\nID: {last_reminder.id}\nLink ID: {last_reminder.link_id}")
    finally:
        session.close()

if __name__ == "__main__":
    verify_schema()