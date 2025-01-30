import os
import logging
import secrets
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

class Environment:
    """Environment constants"""
    DEVELOPMENT = 'development'
    TESTING = 'testing'
    PRODUCTION = 'production'

class SecurityConfig:
    """Security-related configurations"""
    MIN_PASSWORD_LENGTH = 12
    SECURE_HASH_ALGORITHM = 'sha256'
    KEY_DERIVATION_ROUNDS = 100000

class Config:
    """Enhanced configuration class with security features"""
    
    def __init__(self):
        self._load_environment()
        self._setup_logging()
        self._load_and_validate_config()
        
    def _load_environment(self):
        """Load appropriate .env file based on environment"""
        self.ENVIRONMENT = os.getenv('ENVIRONMENT', Environment.DEVELOPMENT)
        
        # Determine environment file
        env_file = '.env'
        if self.ENVIRONMENT == Environment.PRODUCTION:
            env_file = '.env.prod'
        elif self.ENVIRONMENT == Environment.TESTING:
            env_file = '.env.test'
            
        # Get project root directory
        project_root = Path(__file__).parent.parent
        env_path = project_root / env_file
        
        # Load environment variables
        if env_path.exists():
            load_dotenv(env_path)
        else:
            logging.warning(f"Environment file {env_file} not found")
    
    def _setup_logging(self):
        """Configure logging with secure settings"""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_format = os.getenv('LOG_FORMAT', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        if self.ENVIRONMENT == Environment.PRODUCTION:
            # Secure file permissions for log directory
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            log_dir.chmod(0o750)  # rwxr-x---
            
            # Set up file handler with secure permissions
            log_file = log_dir / 'bot.log'
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            
            # Set secure file permissions
            log_file.chmod(0o640)  # rw-r-----
            
            logging.getLogger('').addHandler(file_handler)
        
        logging.basicConfig(level=getattr(logging, log_level), format=log_format)
        self.logger = logging.getLogger(__name__)
    
    def _load_and_validate_config(self):
        """Load and validate all configuration variables"""
        try:
            # Required configurations
            self.TELEGRAM_TOKEN = self._get_required_env('TELEGRAM_TOKEN')
            self.DATABASE_URL = self._get_required_env('DATABASE_URL')
            
            # Optional configurations with defaults
            self.DEBUG = self._get_optional_env('DEBUG', 'False').lower() == 'true'
            self.DB_POOL_SIZE = int(self._get_optional_env('DB_POOL_SIZE', '5'))
            self.DB_MAX_OVERFLOW = int(self._get_optional_env('DB_MAX_OVERFLOW', '10'))
            self.RATE_LIMIT_MESSAGES = int(self._get_optional_env('RATE_LIMIT_MESSAGES', '10'))
            self.RATE_LIMIT_LINKS = int(self._get_optional_env('RATE_LIMIT_LINKS', '5'))
            
            # Security settings
            self.HASH_SALT = self._get_or_generate_salt()
            self.ENCRYPTION_KEY = self._get_or_generate_key()
            
            # Production-specific settings
            if self.ENVIRONMENT == Environment.PRODUCTION:
                self.SENTRY_DSN = self._get_required_env('SENTRY_DSN')
                self.REDIS_URL = self._get_required_env('REDIS_URL')
                self.DEBUG = False  # Force debug to False in production
            
            self._validate_security_settings()
            
        except ValueError as e:
            self.logger.error(f"Configuration error: {str(e)}")
            raise
    
    def _get_required_env(self, key: str) -> str:
        """Get a required environment variable"""
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Required environment variable '{key}' is not set. "
                f"Please check your .env file."
            )
        return value
    
    def _get_optional_env(self, key: str, default: Optional[str] = None) -> str:
        """Get an optional environment variable"""
        return os.getenv(key, default)
    
    def _get_or_generate_salt(self) -> str:
        """Get or generate a secure salt"""
        salt = os.getenv('HASH_SALT')
        if not salt:
            salt = secrets.token_hex(16)
            self.logger.warning("Generated new HASH_SALT as none was provided")
        return salt
    
    def _get_or_generate_key(self) -> str:
        """Get or generate a secure encryption key"""
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            key = secrets.token_urlsafe(32)
            self.logger.warning("Generated new ENCRYPTION_KEY as none was provided")
        return key
    
    def _validate_security_settings(self):
        """Validate security-related settings"""
        if self.ENVIRONMENT == Environment.PRODUCTION:
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production")
            if not self.DATABASE_URL.startswith('postgresql://'):
                raise ValueError("Production must use PostgreSQL database")
            if 'sqlite' in self.DATABASE_URL:
                raise ValueError("SQLite is not allowed in production")
        
        # Validate minimum key lengths
        if len(self.HASH_SALT) < 16:
            raise ValueError("HASH_SALT must be at least 16 characters long")
        if len(self.ENCRYPTION_KEY) < 32:
            raise ValueError("ENCRYPTION_KEY must be at least 32 characters long")

# Create singleton instance
config = Config()