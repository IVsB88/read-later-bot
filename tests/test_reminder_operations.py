# tests/test_reminder_operations.py
import pytest
from datetime import datetime, timedelta, timezone
from models_dir.models import User, Link, Reminder
from database.db_handler import DatabaseHandler
from config.config import Config, Environment

@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables before each test"""
    # Reset Config singleton
    if hasattr(Config, '_instance'):
        Config._instance = None
    
    # Reset DatabaseHandler singleton
    DatabaseHandler.reset()
    
    # Set test environment variables
    monkeypatch.setenv('ENVIRONMENT', 'testing')
    monkeypatch.setenv('DEBUG', 'True')
    monkeypatch.setenv('TELEGRAM_TOKEN', 'test_token')
    monkeypatch.setenv('DATABASE_URL', 'sqlite:///test.db')
    monkeypatch.setenv('HASH_SALT', 'test_salt_1234567890abcdef')
    monkeypatch.setenv('ENCRYPTION_KEY', 'test_key_1234567890abcdef1234567890abcdef')
    monkeypatch.setenv('DB_POOL_SIZE', '1')
    monkeypatch.setenv('DB_MAX_OVERFLOW', '0')
    
    yield

@pytest.fixture
def db_session():
    """Provides a database session for tests"""
    db = DatabaseHandler()
    session = db.get_session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()

def create_test_user(db_session, telegram_id=None, timezone=None):
    """Helper function to create a test user"""
    if telegram_id is None:
        telegram_id = int(datetime.now().timestamp() * 1000)
    
    user = User(
        telegram_id=telegram_id,
        username="test_user",
        first_name="Test",
        timezone=timezone
    )
    db_session.add(user)
    db_session.commit()
    return user

def create_test_link(db_session, user):
    """Helper function to create a test link"""
    link = Link(
        user_id=user.id,
        url="https://test.com"
    )
    db_session.add(link)
    db_session.commit()
    return link

def test_basic_reminder_creation(db_session):
    """Test creating a reminder with default time (9 AM next day)"""
    # Arrange
    user = create_test_user(db_session)
    link = create_test_link(db_session, user)
    
    # Act
    now = datetime.now(timezone.utc)
    next_day_9am = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    reminder = Reminder(
        link_id=link.id,
        remind_at=next_day_9am,
        is_default_time=True
    )
    db_session.add(reminder)
    db_session.commit()
    
    # Assert
    saved_reminder = db_session.query(Reminder).filter_by(link_id=link.id).first()
    assert saved_reminder is not None
    assert saved_reminder.is_default_time is True
    assert saved_reminder.remind_at.replace(tzinfo=timezone.utc).hour == 9
    assert saved_reminder.status == 'pending'

def test_custom_reminder_time(db_session):
    """Test setting a custom reminder time"""
    # Arrange
    user = create_test_user(db_session, timezone="2")  # UTC+2
    link = create_test_link(db_session, user)
    
    # Act - Set reminder for tomorrow at user's timezone
    now = datetime.now(timezone.utc)
    user_local_time = now + timedelta(hours=2)  # Apply user's timezone offset
    reminder_time = user_local_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    utc_reminder_time = reminder_time - timedelta(hours=2)  # Convert back to UTC
    
    reminder = Reminder(
        link_id=link.id,
        remind_at=utc_reminder_time,
        is_default_time=False
    )
    db_session.add(reminder)
    db_session.commit()
    
    # Assert
    saved_reminder = db_session.query(Reminder).filter_by(link_id=link.id).first()
    assert saved_reminder is not None
    assert saved_reminder.is_default_time is False
    assert saved_reminder.remind_at.replace(tzinfo=timezone.utc) == utc_reminder_time.replace(tzinfo=timezone.utc)

def test_reminder_snooze(db_session):
    """Test snoozing a reminder"""
    # Arrange
    user = create_test_user(db_session)
    link = create_test_link(db_session, user)
    now = datetime.now(timezone.utc)
    
    reminder = Reminder(
        link_id=link.id,
        remind_at=now,
        is_default_time=True
    )
    db_session.add(reminder)
    db_session.commit()
    
    # Act - Snooze the reminder
    next_day_9am = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    reminder.remind_at = next_day_9am
    reminder.is_snoozed = True
    reminder.snooze_count += 1
    db_session.commit()
    
    # Assert
    assert reminder.snooze_count == 1
    assert reminder.is_snoozed is True
    assert reminder.remind_at.replace(tzinfo=timezone.utc).hour == 9

def test_get_due_reminders(db_session):
    """Test fetching due reminders"""
    try:
        # Clean up existing reminders first
        db_session.query(Reminder).delete()
        db_session.commit()
        
        # Arrange
        user = create_test_user(db_session)
        link = create_test_link(db_session, user)
        now = datetime.now(timezone.utc)
        
        # Create an overdue reminder
        reminder = Reminder(
            link_id=link.id,
            remind_at=now - timedelta(minutes=5),
            status='pending'
        )
        db_session.add(reminder)
        db_session.commit()
        
        # Act - Use a more specific query
        due_reminders = (
            db_session.query(Reminder)
            .filter(
                Reminder.status == 'pending',
                Reminder.remind_at <= now,
                Reminder.link_id == link.id  # Make sure we only get reminders for our test link
            )
            .all()
        )
        
        # Assert
        assert len(due_reminders) == 1
        assert due_reminders[0].id == reminder.id
        
    finally:
        # Clean up after test
        db_session.query(Reminder).filter(Reminder.link_id == link.id).delete()
        db_session.commit()

def test_reminder_status_updates(db_session):
    """Test updating reminder status"""
    # Arrange
    user = create_test_user(db_session)
    link = create_test_link(db_session, user)
    now = datetime.now(timezone.utc)
    
    reminder = Reminder(
        link_id=link.id,
        remind_at=now,
        status='pending'
    )
    db_session.add(reminder)
    db_session.commit()
    
    # Act
    reminder.status = 'sent'
    reminder.last_reminded_at = now
    db_session.commit()
    
    # Assert
    updated_reminder = db_session.query(Reminder).filter_by(id=reminder.id).first()
    assert updated_reminder.status == 'sent'
    assert updated_reminder.last_reminded_at is not None

def test_user_selecting_reminder_time(db_session):
    """Test user selecting a specific reminder time"""
    # Arrange
    user = create_test_user(db_session, timezone="3")  # UTC+3
    link = create_test_link(db_session, user)
    now = datetime.now(timezone.utc)
    
    # Act - Simulate user selecting "In 2 Days" option
    user_local_time = now + timedelta(hours=3)  # Apply user's timezone offset
    reminder_time = user_local_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=2)
    utc_reminder_time = reminder_time - timedelta(hours=3)  # Convert back to UTC
    
    reminder = Reminder(
        link_id=link.id,
        remind_at=utc_reminder_time,
        is_default_time=False
    )
    db_session.add(reminder)
    db_session.commit()
    
    # Assert
    saved_reminder = db_session.query(Reminder).filter_by(link_id=link.id).first()
    assert saved_reminder is not None
    assert saved_reminder.is_default_time is False
    assert saved_reminder.remind_at.replace(tzinfo=timezone.utc) == utc_reminder_time.replace(tzinfo=timezone.utc)

def test_user_skipping_reminder_with_timezone(db_session):
    """Test when user skips reminder setting with timezone set"""
    # Arrange
    user = create_test_user(db_session, timezone="5.5")  # UTC+5:30
    link = create_test_link(db_session, user)
    now = datetime.now(timezone.utc)
    
    # Act - Simulate user clicking "Skip"
    user_local_time = now + timedelta(hours=5, minutes=30)
    reminder_time = user_local_time.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    utc_reminder_time = reminder_time - timedelta(hours=5, minutes=30)
    
    reminder = Reminder(
        link_id=link.id,
        remind_at=utc_reminder_time,
        is_default_time=True
    )
    db_session.add(reminder)
    db_session.commit()
    
    # Assert
    saved_reminder = db_session.query(Reminder).filter_by(link_id=link.id).first()
    assert saved_reminder is not None
    assert saved_reminder.is_default_time is True
    assert saved_reminder.remind_at.replace(tzinfo=timezone.utc) == utc_reminder_time.replace(tzinfo=timezone.utc)

def test_user_skipping_reminder_without_timezone(db_session):
    """Test when user skips reminder setting without timezone set"""
    # Arrange
    user = create_test_user(db_session, timezone=None)  # No timezone set
    link = create_test_link(db_session, user)
    now = datetime.now(timezone.utc)
    
    # Act - Use server time (UTC) for 9 AM next day
    reminder_time = now.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
    
    reminder = Reminder(
        link_id=link.id,
        remind_at=reminder_time,
        is_default_time=True
    )
    db_session.add(reminder)
    db_session.commit()
    
    # Assert
    saved_reminder = db_session.query(Reminder).filter_by(link_id=link.id).first()
    assert saved_reminder is not None
    assert saved_reminder.is_default_time is True
    assert saved_reminder.remind_at.replace(tzinfo=timezone.utc).hour == 9  # Should be 9 AM UTC