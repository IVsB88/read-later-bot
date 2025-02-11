# utils/logging_config.py
import logging
import logging.handlers
import re
from typing import Dict, Any
from config.config import Config

config = Config.get_instance()
class SensitiveDataFilter(logging.Filter):
    """Enhanced filter that masks sensitive data in log records"""
    
    def __init__(self):
        super().__init__()
        self.patterns = [
            # More comprehensive bot token pattern
            (r'bot[0-9]+:[A-Za-z0-9-_]{35}', 'BOT_TOKEN_MASKED'),
            # Match the full URL with token
            (r'https://api\.telegram\.org/bot[0-9]+:[A-Za-z0-9-_]+/', 
             'https://api.telegram.org/bot[MASKED]/'),
            (r'DATABASE_URL=[^\s]+', 'DATABASE_URL_MASKED'),
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg'):
            if isinstance(record.msg, str):
                msg = record.msg
                for pattern, mask in self.patterns:
                    msg = re.sub(pattern, mask, msg)
                record.msg = msg
            elif isinstance(record.msg, dict):
                record.msg = self.mask_dict(record.msg)
                
        # Also mask args if they exist
        if record.args:
            args = list(record.args)
            for i, arg in enumerate(args):
                if isinstance(arg, str):
                    for pattern, mask in self.patterns:
                        args[i] = re.sub(pattern, mask, arg)
            record.args = tuple(args)
        return True
    
    def mask_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        masked = d.copy()
        for k, v in masked.items():
            masked[k] = self.mask_value(v)
        return masked
    
    def mask_value(self, value: Any) -> Any:
        if isinstance(value, str):
            for pattern, mask in self.patterns:
                value = re.sub(pattern, mask, value)
        return value

def setup_logging():
    """Configure logging with appropriate levels for different components"""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    # Create formatter with more readable format
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Set specific log levels for different components
    if config.DEBUG:
        # Development settings
        root_logger.setLevel(logging.INFO)
        
        # Your application logs (full debug)
        logging.getLogger('__main__').setLevel(logging.DEBUG)
        logging.getLogger('bot').setLevel(logging.DEBUG)
        
        # HTTP client (minimal logs)
        logging.getLogger('httpx').setLevel(logging.WARNING)  # Only warnings and errors
        
        # Telegram bot logs (important info only)
        logging.getLogger('telegram').setLevel(logging.INFO)
        
        # Job scheduler (important info only)
        logging.getLogger('apscheduler').setLevel(logging.INFO)
    else:
        # Production settings
        root_logger.setLevel(logging.INFO)
        for logger_name in ['httpx', 'telegram', 'apscheduler']:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Add sensitive data filter to root logger
    sensitive_filter = SensitiveDataFilter()
    root_logger.addFilter(sensitive_filter)

def log_action(action: str, details: dict = None, logger_name: str = None):
    """Enhanced logging function that respects debug mode"""
    logger_to_use = logging.getLogger(logger_name) if logger_name else logging.getLogger(__name__)
    
    if config.DEBUG:
        log_msg = f"Action: {action}"
        if details:
            # Format details for better readability
            details_str = "\n".join(f"  {k}: {v}" for k, v in details.items())
            log_msg += f"\nDetails:\n{details_str}"
        logger_to_use.debug(log_msg)
    else:
        logger_to_use.info(f"Action: {action}")
        if details and 'error' in details:
            logger_to_use.error(f"Error in {action}: {details['error']}")