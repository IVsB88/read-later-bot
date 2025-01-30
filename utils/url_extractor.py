# utils/url_extractor.py
import re
import logging
from urllib.parse import urlparse
from typing import List, Optional

class URLValidator:
    # Standard maximum URL length (based on IE and Safari limits)
    MAX_URL_LENGTH = 2083
    
    # Only allow http and https schemes
    ALLOWED_SCHEMES = {'http', 'https'}
    
    # Strict URL pattern
    URL_PATTERN = r'^https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/=]*)$'
    
    # User-friendly error messages
    ERROR_MESSAGES = {
        'length': "URL is too long. Please provide a shorter URL.",
        'scheme': "Invalid URL. The URL must start with 'http://' or 'https://'",
        'pattern': "Invalid URL format. Please check the URL and try again.",
        'domain': "Invalid URL. Please ensure the URL includes a valid domain name."
    }
    
    @classmethod
    def validate_url(cls, url: str) -> tuple[bool, str]:
        """
        Validates a URL for security and format.
        Returns a tuple of (is_valid, error_message).
        """
        try:
            # Check URL length
            if not url or len(url) > cls.MAX_URL_LENGTH:
                logging.warning(f"URL length validation failed: {url[:50]}...")
                return False, cls.ERROR_MESSAGES['length']
            
            # Basic pattern matching
            if not re.match(cls.URL_PATTERN, url):
                logging.warning(f"URL pattern matching failed: {url[:50]}")
                return False, cls.ERROR_MESSAGES['pattern']
            
            # Parse URL for deeper validation
            parsed = urlparse(url)
            
            # Validate scheme
            if parsed.scheme not in cls.ALLOWED_SCHEMES:
                logging.warning(f"Invalid URL scheme: {parsed.scheme}")
                return False, cls.ERROR_MESSAGES['scheme']
            
            # Validate netloc (domain) exists
            if not parsed.netloc:
                logging.warning("Missing domain in URL")
                return False, cls.ERROR_MESSAGES['domain']
            
            return True, ""
            
        except Exception as e:
            logging.error(f"URL validation error: {str(e)}")
            return False, cls.ERROR_MESSAGES['pattern']

def extract_urls(message: str) -> tuple[List[str], List[str]]:
    """
    Extracts and validates URLs from a message.
    Returns a tuple of (valid_urls, error_messages).
    Only validates URLs that start with http:// or https://.
    """
    if not message:
        return [], []
        
    try:
        # Extract only potential http(s) URLs
        potential_urls = re.findall(r'https?://[^\s]+', message)
        
        # Validate each URL
        valid_urls = []
        error_messages = []
        
        for url in potential_urls:
            is_valid, error_msg = URLValidator.validate_url(url)
            if is_valid:
                valid_urls.append(url)
            elif error_msg:  # Only add error message if it's an attempted http(s) URL
                error_messages.append(error_msg)
                logging.warning(f"Invalid HTTP(S) URL found: {url[:50]}")
        
        return valid_urls, error_messages
        
    except Exception as e:
        logging.error(f"Error during URL extraction: {str(e)}")
        return [], []