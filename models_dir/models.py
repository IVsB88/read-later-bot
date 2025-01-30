# models_dir/models.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, CheckConstraint, Index
from sqlalchemy.orm import declarative_base 
from sqlalchemy.orm import relationship
from sqlalchemy.orm import validates
from datetime import datetime, timezone
from urllib.parse import urlparse
import logging

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255))
    first_name = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))  # Note the timezone=True
    timezone = Column(String, nullable=True)
    has_set_timezone = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    links = relationship("Link", back_populates="user")

class Link(Base):
    __tablename__ = 'links'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    url = Column(String(2083), nullable=False)  # Maximum URL length supported by browsers
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_read = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="links")
    reminders = relationship("Reminder", back_populates="link", cascade="all, delete-orphan")

    # Add essential constraints and indexes
    __table_args__ = (
        # Check URL length
        CheckConstraint('LENGTH(url) <= 2083', name='check_url_length'),
        # Check URL starts with http:// or https://
        CheckConstraint(
            "url SIMILAR TO 'https?://%'",
            name='check_url_format'
        ),
        # Add index for user's links queries
        Index('idx_links_user_created', user_id, created_at),
    )

class Reminder(Base):
    __tablename__ = 'reminders'
    
    id = Column(Integer, primary_key=True)
    link_id = Column(Integer, ForeignKey('links.id'), nullable=False)
    remind_at = Column(DateTime(timezone=True), nullable=False)
    is_default_time = Column(Boolean, default=False)
    is_snoozed = Column(Boolean, default=False)
    snooze_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default='pending')
    last_reminded_at = Column(DateTime(timezone=True))
    
    link = relationship("Link", back_populates="reminders")

class UserAnalytics(Base):
    __tablename__ = 'user_analytics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    
    # Engagement
    total_links_saved = Column(Integer, default=0)
    active_days_count = Column(Integer, default=0)
    last_activity = Column(DateTime)
    
    # Reminder Behavior
    manual_reminder_count = Column(Integer, default=0)  # Set custom time
    default_passive_count = Column(Integer, default=0)  # No action taken
    active_skip_count = Column(Integer, default=0)      # Clicked skip
    default_reminder_count = Column(Integer, default=0)
    total_snoozes = Column(Integer, default=0)
    
    # Conversion
    completed_reminders = Column(Integer, default=0)
    missed_reminders = Column(Integer, default=0)
    reminder_completion_rate = Column(Float, default=0.0)

    # Relationship
    user = relationship("User", backref="analytics")
    