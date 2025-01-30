import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models_dir.models import Base
from config.config import Config

# Add the project root directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

engine = create_engine(Config.DATABASE_URL)
Session = sessionmaker(bind=engine)

def init_db():
    # Only create tables if they don't already exist
    Base.metadata.create_all(engine)
    print("Database initialized.")

if __name__ == "__main__":
    init_db()