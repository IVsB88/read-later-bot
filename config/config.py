# config/config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

class Environment:
    DEVELOPMENT = 'development'
    TESTING = 'testing'
    PRODUCTION = 'production'

class Config:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        self._load_environment()
        self._initialized = True
        
    def _load_environment(self):
        """Load appropriate .env file based on environment"""
        self.logger.info("Starting environment loading...")
        
        # Check if we're in test mode
        if 'ENV_FILE' in os.environ:
            env_path = Path(os.environ['ENV_FILE'])
            self.logger.info(f"Loading test environment from: {env_path}")
            if env_path.exists():
                load_dotenv(env_path, override=True)
                self.logger.info(f"Loaded test environment file")
            else:
                self.logger.warning(f"Test environment file not found: {env_path}")
        else:
            # Normal environment loading
            project_root = Path(__file__).parent.parent
            env_path = project_root / '.env'
            self.logger.info(f"Loading production environment from: {env_path}")
            if env_path.exists():
                load_dotenv(env_path, override=True)
                self.logger.info("Loaded production environment file")
        
        # Get environment setting
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', Environment.DEVELOPMENT)
        self.logger.info(f"Environment set to: {self.ENVIRONMENT}")
        
        # Load all settings
        self._load_required_settings()
        self._load_optional_settings()
        self._validate_security_settings()
    
    def _load_required_settings(self):
        """Load and validate required settings"""
        # Bot settings
        self.TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
        self.BOT_USERNAME = os.getenv('BOT_USERNAME')

        # Database settings
        self.DATABASE_URL = os.getenv('DATABASE_URL')
        self.DB_POOL_SIZE = int(os.getenv('DB_POOL_SIZE', '5'))
        self.DB_MAX_OVERFLOW = int(os.getenv('DB_MAX_OVERFLOW', '10'))
        
        # Validate required settings
        if not self.TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN is required")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is required")
        if not self.BOT_USERNAME:
            raise ValueError("BOT_USERNAME is required")
            
    def _load_optional_settings(self):
        """Load optional settings with defaults"""
        # Debug and logging
        self.DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
        self.LOG_FORMAT = os.getenv('LOG_FORMAT', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # Security settings
        self.HASH_SALT = os.getenv('HASH_SALT')
        self.ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
        
        # Rate limiting
        self.RATE_LIMIT_MESSAGES = int(os.getenv('RATE_LIMIT_MESSAGES', '10'))
        self.RATE_LIMIT_LINKS = int(os.getenv('RATE_LIMIT_LINKS', '5'))
        
        # Reminder settings
        self.DEFAULT_REMINDER_HOUR = int(os.getenv('DEFAULT_REMINDER_HOUR', '9'))
        self.REMINDER_CHECK_INTERVAL = int(os.getenv('REMINDER_CHECK_INTERVAL', '300'))  # 5 minutes
        self.MISSED_REMINDER_THRESHOLD = int(os.getenv('MISSED_REMINDER_THRESHOLD', '24'))  # hours
        
        # Timeouts
        self.DB_CONNECTION_TIMEOUT = int(os.getenv('DB_CONNECTION_TIMEOUT', '10'))
        self.API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))
        
        # Production-only settings
        if self.ENVIRONMENT == Environment.PRODUCTION:
            self.SENTRY_DSN = os.getenv('SENTRY_DSN')
            self.REDIS_URL = os.getenv('REDIS_URL')
            
            # These are required in production
            if not self.SENTRY_DSN:
                raise ValueError("SENTRY_DSN is required in production")
            if not self.REDIS_URL:
                raise ValueError("REDIS_URL is required in production")
    
    def _validate_security_settings(self):
        """Validate security-related settings"""
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if not self.DATABASE_URL.startswith('postgresql://'):
                raise ValueError("Production must use PostgreSQL database")
            if 'sqlite' in self.DATABASE_URL:
                raise ValueError("SQLite is not allowed in production")
        
        # Validate security settings if they exist
        if self.HASH_SALT and len(self.HASH_SALT) < 16:
            raise ValueError("HASH_SALT must be at least 16 characters long")
        if self.ENCRYPTION_KEY and len(self.ENCRYPTION_KEY) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters long")

    @classmethod
    def reset(cls):
        """Reset the singleton instance (useful for testing)"""
        cls._instance = None

    @classmethod
    def get_instance(cls):
        """Get or create Config instance"""
        if cls._instance is None:
            return cls()
        return cls._instance