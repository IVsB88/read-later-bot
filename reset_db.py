import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models_dir.models import Base, Link, Reminder
from database.db_handler import DatabaseHandler

def reset_tables():
    db = DatabaseHandler()
    Base.metadata.drop_all(db.engine)
    Base.metadata.create_all(db.engine)
    print("Tables reset successfully")

def check_data():
    db = DatabaseHandler()
    session = db.get_session()
    try:
        link_count = session.query(Link).count()
        reminder_count = session.query(Reminder).count()
        print(f"\nCurrent data:\nLinks: {link_count}\nReminders: {reminder_count}")
    finally:
        session.close()

if __name__ == "__main__":
    reset_tables()
    check_data()