# tests/conftest.py
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models_dir.models import Base

# --- Environment Variable Setup ---
# Set required environment variables for testing the configuration.
# These will be in place before any tests (or module-level code) runs.
os.environ["ENVIRONMENT"] = "production"
os.environ["TELEGRAM_TOKEN"] = "test_123_token"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["HASH_SALT"] = "test_salt_which_is_long_enough"
os.environ["ENCRYPTION_KEY"] = "test_key_that_is_long_enough_for_production!!"
os.environ["DEBUG"] = "False"
os.environ["SENTRY_DSN"] = "dummy_sentry_dsn"
os.environ["REDIS_URL"] = "redis://localhost:6379"

# Optionally, if your config uses load_dotenv and you want to prevent it
# from overwriting these settings, you might patch load_dotenv here or in a fixture.
# For example, you can do:
# from config.config import load_dotenv
# load_dotenv = lambda *args, **kwargs: None

# --- Existing Database Fixtures ---
@pytest.fixture(scope="function")
def test_db():
    """Create a test database"""
    # Use an in-memory SQLite database for tests
    TEST_DATABASE_URL = "sqlite:///:memory:"
    engine = create_engine(TEST_DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create a session factory
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
