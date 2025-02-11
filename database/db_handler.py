import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from models_dir.models import Base, User, Link, Reminder, UserAnalytics  # Added UserAnalytics
from config.config import Config

logger = logging.getLogger(__name__)
config = Config.get_instance()

class DatabaseHandler:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.init_db()
            self._initialized = True
    
    def init_db(self):
        try:
            # Enhanced pool settings
            pool_settings = {
                'poolclass': QueuePool,
                'pool_size': config.DB_POOL_SIZE,
                'max_overflow': config.DB_MAX_OVERFLOW,
                'pool_timeout': 30,
                'pool_recycle': 1800,
                'pool_pre_ping': True
            }

            # Production-specific settings
            if config.ENVIRONMENT == 'production':
                pool_settings.update({
                    'connect_args': {
                        'connect_timeout': 10,
                        'sslmode': 'verify-full'
                    }
                })
            else:
                # Development settings
                pool_settings.update({
                    'connect_args': {
                        'connect_timeout': 10,
                    }
                })

            self.engine = create_engine(
                config.DATABASE_URL,
                **pool_settings
            )
            
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                expire_on_commit=False
            )
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    def get_session(self):
        """Get a new database session"""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
        """Context manager for database sessions"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()

    def create_user(self, telegram_id, username=None, first_name=None):
        """Create a new user with secure session handling"""
        with self.session_scope() as session:
            try:
                user = session.query(User).filter_by(telegram_id=telegram_id).first()
                if not user:
                    user = User(
                        telegram_id=telegram_id,
                        username=username,
                        first_name=first_name
                    )
                    session.add(user)
                return user
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                raise

    def save_link(self, user_id, url, title=None, content_type=None):
        """Save a link with secure session handling"""
        with self.session_scope() as session:
            try:
                link = Link(
                    user_id=user_id,
                    url=url,
                    title=title,
                    content_type=content_type
                )
                session.add(link)
                
                # Create default reminder for tomorrow at 9 AM
                tomorrow_9am = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
                reminder = Reminder(
                    link=link,
                    remind_at=tomorrow_9am,
                    is_default_time=True
                )
                session.add(reminder)
                
                # Get IDs before closing session
                link_id = link.id
                reminder_id = reminder.id
                
                return link_id, reminder_id
                
            except Exception as e:
                logger.error(f"Error saving link: {str(e)}")
                raise

    def schedule_reminder(self, user_id, link_id, delta):
        """Schedule a reminder with secure session handling"""
        with self.session_scope() as session:
            try:
                link = session.query(Link).filter_by(id=link_id, user_id=user_id).first()
                if not link:
                    raise ValueError("Link not found or does not belong to the user")

                remind_at = datetime.now() + delta
                reminder = Reminder(
                    link_id=link.id,
                    remind_at=remind_at,
                    is_default_time=False
                )
                session.add(reminder)
                return reminder
                
            except Exception as e:
                logger.error(f"Error scheduling reminder: {str(e)}")
                raise


    def update_user_analytics(self, user_id, action_type, session=None):
        """Update user analytics with proper error handling"""
        session_created_here = False
        try:
            if session is None:
                session = self.get_session()
                session_created_here = True
                
            analytics = session.query(UserAnalytics).filter_by(user_id=user_id).first()
            if not analytics:
                analytics = UserAnalytics(user_id=user_id)
                session.add(analytics)
                session.commit()  # Commit new analytics record
            
            # Update metrics based on action type
            if action_type == 'link_saved':
                analytics.total_links_saved += 1
            elif action_type == 'manual_reminder':
                analytics.manual_reminder_count += 1
            elif action_type == 'default_passive':
                analytics.default_passive_count += 1
            elif action_type == 'active_skip':
                analytics.active_skip_count += 1
            elif action_type == 'reminder_completed':
                analytics.completed_reminders += 1
            elif action_type == 'reminder_missed':
                analytics.missed_reminders += 1
            elif action_type == 'snooze':
                analytics.total_snoozes += 1
            
            session.commit()
            
        except Exception as e:
            logger.error(f"Error updating analytics: {str(e)}")
            if session:
                session.rollback()
            raise
        finally:
            if session and session_created_here:
                session.close()