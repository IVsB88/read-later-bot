# tests/test_link_operations.py
import pytest
import logging
from sqlalchemy.orm import Session
from models_dir.models import User, Link, Reminder
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def test_user(db_session):
    """Fixture to create a test user"""
    user = User(telegram_id=123456)
    db_session.add(user)
    db_session.commit()
    return user

def test_save_link(db_session: Session, test_user: User):
    """Test saving a link for a user"""
    try:
        # Arrange
        url = "https://example.com"
        
        # Create link
        link = Link(
            user_id=test_user.id,
            url=url
        )
        db_session.add(link)
        db_session.commit()
        
        # Query to verify
        saved_link = db_session.query(Link).filter_by(url=url).first()
        
        # Assert
        assert saved_link is not None
        assert saved_link.url == url
        assert saved_link.user_id == test_user.id
        assert saved_link.is_read is False

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

def test_multiple_links_for_user(db_session: Session, test_user: User):
    """Test user can save multiple links"""
    try:
        # Create multiple links
        urls = [f"https://example{i}.com" for i in range(3)]
        for url in urls:
            link = Link(user_id=test_user.id, url=url)
            db_session.add(link)
        db_session.commit()
        
        # Query to verify
        user_links = db_session.query(Link).filter_by(user_id=test_user.id).all()
        
        # Assert
        assert len(user_links) == 3
        assert all(link.user_id == test_user.id for link in user_links)
        assert all(link.is_read is False for link in user_links)

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise

def test_mark_link_as_read(db_session: Session, test_user: User):
    """Test marking a link as read"""
    try:
        # Create a link
        url = "https://example.com"
        link = Link(user_id=test_user.id, url=url)
        db_session.add(link)
        db_session.commit()
        
        # Mark as read
        link.is_read = True
        db_session.commit()
        
        # Query to verify
        saved_link = db_session.query(Link).filter_by(url=url).first()
        assert saved_link.is_read is True

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        raise