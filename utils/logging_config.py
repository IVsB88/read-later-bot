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
            # Bot token pattern
            (r'bot[0-9]+:[A-Za-z0-9_-]{30,}', '[MASKED_BOT_TOKEN]'),
            # Database URLs
            (r'postgresql://[^@]+@[^/\s]+', '[MASKED_DB_URL]'),
            # API URLs
            (r'https://api\.telegram\.org/bot[^/]+', '[MASKED_API_URL]'),
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
    from config.config import Config
    config = Config.get_instance()
    
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
    
    # Add handler to root logger
    root_logger.addHandler(console_handler)
    
    # Add sensitive data filter to root logger AND console handler
    sensitive_filter = SensitiveDataFilter()
    root_logger.addFilter(sensitive_filter)
    console_handler.addFilter(sensitive_filter)  # Add filter to handler too
    
    # Set log levels after adding filters
    if config.DEBUG:
        root_logger.setLevel(logging.INFO)
        logging.getLogger('__main__').setLevel(logging.DEBUG)
        logging.getLogger('bot').setLevel(logging.DEBUG)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('telegram').setLevel(logging.INFO)
        logging.getLogger('apscheduler').setLevel(logging.INFO)
    else:
        root_logger.setLevel(logging.INFO)
        for logger_name in ['httpx', 'telegram', 'apscheduler']:
            logging.getLogger(logger_name).setLevel(logging.WARNING)

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