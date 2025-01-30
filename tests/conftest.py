# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_dir.models import Base

@pytest.fixture(scope="function")
def test_db():
    """Create a test database"""
    # Use in-memory SQLite database
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session factory
    TestingSessionLocal = sessionmaker(bind=engine)
    
    yield TestingSessionLocal
    
    # Drop all tables after each test
    Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(test_db):
    """Create a new database session for each test"""
    session = test_db()
    try:
        yield session
    finally:
        session.rollback()
        session.close()