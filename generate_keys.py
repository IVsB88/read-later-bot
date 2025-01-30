import secrets

def generate_security_keys():
    """Generate secure values for environment variables"""
    # Generate a secure salt (32 characters)
    salt = secrets.token_hex(16)
    
    # Generate a secure encryption key (44 characters)
    encryption_key = secrets.token_urlsafe(32)
    
    print("\n=== Generated Security Keys ===\n")
    print("Add these to your .env file:\n")
    print(f"HASH_SALT={salt}")
    print(f"ENCRYPTION_KEY={encryption_key}")
    print("\nMake sure to keep these values secure and never commit them to version control!")

if __name__ == "__main__":
    generate_security_keys()