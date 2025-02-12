from config.config import Config
import os

config = Config.get_instance()

def verify_config():
    """Verify configuration loading and settings"""
    print("\n=== Configuration Verification ===\n")
    
    # Check environment
    print(f"Current Environment: {config.ENVIRONMENT}")
    
    # Check essential configurations
    print("\nEssential Configurations:")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Database Pool Size: {config.DB_POOL_SIZE}")
    print(f"Database Max Overflow: {config.DB_MAX_OVERFLOW}")
    
    # Check rate limits
    print("\nRate Limits:")
    print(f"Message Rate Limit: {config.RATE_LIMIT_MESSAGES} per minute")
    print(f"Link Rate Limit: {config.RATE_LIMIT_LINKS} per minute")
    
    # Verify security settings (without exposing values)
    print("\nSecurity Settings:")
    print(f"Hash Salt Present: {'Yes' if config.HASH_SALT else 'No'}")
    print(f"Encryption Key Present: {'Yes' if config.ENCRYPTION_KEY else 'No'}")
    
    # Environment-specific checks
    if config.ENVIRONMENT == 'production':
        print("\nProduction-specific settings:")
        print(f"Sentry DSN Present: {'Yes' if hasattr(config, 'SENTRY_DSN') else 'No'}")
        print(f"Redis URL Present: {'Yes' if hasattr(config, 'REDIS_URL') else 'No'}")
    
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    try:
        verify_config()
    except Exception as e:
        print(f"\nError during verification: {str(e)}")