# tests/test_db_handler.py
import pytest
import logging
from sqlalchemy.orm import Session
from models_dir.models import User

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_create_user(db_session: Session):
    """Test creating a new user"""
    try:
        # Arrange
        telegram_id = 123456
        username = "test_user"
        first_name = "Test"

        # Create user directly in session
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        db_session.add(user)
        db_session.commit()

        # Query to verify
        saved_user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
        
        # Assert
        assert saved_user is not None
        assert saved_user.telegram_id == telegram_id
        assert saved_user.username == username
        assert saved_user.first_name == first_name

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

def test_create_duplicate_user(db_session: Session):
    """Test creating a user that already exists"""
    try:
        # Arrange
        telegram_id = 123456
        username = "test_user"
        first_name = "Test"

        # Create first user directly
        user1 = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name
        )
        db_session.add(user1)
        db_session.commit()

        # Try to query the user back
        user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
        assert user is not None
        assert user.username == username

        # Try to create a second user with the same telegram_id
        user2 = User(
            telegram_id=telegram_id,
            username="different_username",
            first_name="Different"
        )
        db_session.add(user2)
        
        # This should raise an IntegrityError
        with pytest.raises(Exception) as excinfo:
            db_session.commit()
        
        assert "UNIQUE constraint failed" in str(excinfo.value)

        # Verify the original user wasn't changed
        db_session.rollback()  # Roll back the failed transaction
        user = db_session.query(User).filter_by(telegram_id=telegram_id).first()
        assert user.username == username
        assert user.first_name == first_name

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise