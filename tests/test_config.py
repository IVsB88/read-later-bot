# tests/test_config.py
import pytest
import os
import logging
from pathlib import Path
from config.config import Config, Environment

# Set up logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest.fixture(autouse=True)
def clean_env():
    """Clean environment variables before each test"""
    # Store original environ
    original_environ = dict(os.environ)
    
    # Remove relevant environment variables
    env_vars = [
        'ENVIRONMENT', 'TELEGRAM_TOKEN', 'DATABASE_URL', 'DEBUG', 
        'HASH_SALT', 'ENCRYPTION_KEY', 'SENTRY_DSN', 'REDIS_URL',
        'BOT_USERNAME', 'ENV_FILE'
    ]
    
    for var in env_vars:
        if var in os.environ:
            del os.environ[var]
    
    # Reset Config singleton
    Config.reset()
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_environ)
    Config.reset()

def write_env_file(path, content):
    """Write environment file with proper formatting"""
    # Remove leading spaces from content
    cleaned_content = "\n".join(line.lstrip() for line in content.splitlines())
    path.write_text(cleaned_content)
    logger.debug(f"Wrote env file to {path} with content:\n{cleaned_content}")

def test_default_environment(tmp_path):
    """Test that environment defaults to development when not specified"""
    env_file = tmp_path / '.env'
    write_env_file(env_file, """
    TELEGRAM_TOKEN=test_token
    DATABASE_URL=sqlite:///test.db
    BOT_USERNAME=test_bot
    """)
    
    os.environ['ENV_FILE'] = str(env_file)
    config = Config()
    assert config.ENVIRONMENT == Environment.DEVELOPMENT

def test_development_environment(tmp_path):
    """Test development environment loading"""
    env_file = tmp_path / '.env'
    write_env_file(env_file, """
    ENVIRONMENT=development
    TELEGRAM_TOKEN=test_token
    DATABASE_URL=postgresql://user:pass@localhost:5432/db
    BOT_USERNAME=test_bot
    DEBUG=True
    """)
    
    os.environ['ENV_FILE'] = str(env_file)
    config = Config()
    assert config.ENVIRONMENT == Environment.DEVELOPMENT
    assert config.DEBUG is True

def test_testing_environment(tmp_path):
    """Test testing environment loading"""
    env_file = tmp_path / '.env'
    write_env_file(env_file, """
    ENVIRONMENT=testing
    TELEGRAM_TOKEN=test_token
    DATABASE_URL=sqlite:///test.db
    BOT_USERNAME=test_bot
    DEBUG=True
    """)
    
    os.environ['ENV_FILE'] = str(env_file)
    config = Config()
    assert config.ENVIRONMENT == Environment.TESTING
    assert config.DATABASE_URL == 'sqlite:///test.db'

def test_production_environment(tmp_path):
    """Test production environment loading"""
    env_file = tmp_path / '.env'
    write_env_file(env_file, """
    ENVIRONMENT=production
    TELEGRAM_TOKEN=prod_token
    DATABASE_URL=postgresql://user:pass@prod:5432/db
    BOT_USERNAME=prod_bot
    SENTRY_DSN=test_sentry
    REDIS_URL=redis://localhost
    DEBUG=False
    """)
    
    os.environ['ENV_FILE'] = str(env_file)
    config = Config()
    assert config.ENVIRONMENT == Environment.PRODUCTION
    assert config.DEBUG is False
    assert hasattr(config, 'SENTRY_DSN')
    assert hasattr(config, 'REDIS_URL')

def test_security_settings(tmp_path):
    """Test security-related settings"""
    env_file = tmp_path / '.env'
    write_env_file(env_file, """
    ENVIRONMENT=development
    TELEGRAM_TOKEN=test_token
    DATABASE_URL=postgresql://user:pass@localhost:5432/db
    BOT_USERNAME=test_bot
    HASH_SALT=test_salt_long_enough_16
    ENCRYPTION_KEY=test_encryption_key_must_be_at_least_32_chars
    """)
    
    os.environ['ENV_FILE'] = str(env_file)
    config = Config()
    assert len(config.HASH_SALT) >= 16
    assert len(config.ENCRYPTION_KEY) >= 32

def test_invalid_security_settings(tmp_path):
    """Test that invalid security settings raise errors"""
    env_file = tmp_path / '.env'
    write_env_file(env_file, """
    ENVIRONMENT=production
    TELEGRAM_TOKEN=test_token
    DATABASE_URL=postgresql://user:pass@localhost:5432/db
    BOT_USERNAME=test_bot
    HASH_SALT=short
    ENCRYPTION_KEY=short
    """)
    
    os.environ['ENV_FILE'] = str(env_file)
    with pytest.raises(ValueError):
        Config()

def test_missing_required_settings(tmp_path):
    """Test that missing required settings raise errors"""
    env_file = tmp_path / '.env'
    write_env_file(env_file, """
    ENVIRONMENT=development
    # Missing required settings
    """)
    
    os.environ['ENV_FILE'] = str(env_file)
    with pytest.raises(ValueError):
        Config()