# utils/logging_config.py
import logging
import os
from pathlib import Path
import re
from config.config import Config, Environment

class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data in log records"""
    def __init__(self):
        super().__init__()
        self.patterns = [
            (r'bot[0-9]+:[A-Za-z0-9-_]{35,}', 'BOT_TOKEN_MASKED'),
            (r'bot[0-9]+:[A-Za-z0-9-_]+', 'BOT_TOKEN_MASKED'),  # Shorter pattern for test tokens
            (r'https://api\.telegram\.org/bot[0-9]+:[A-Za-z0-9-_]+', 
            'https://api.telegram.org/bot[MASKED]'),
            (r'https://api\.telegram\.org/BOT_TOKEN_MASKED', 
            'https://api.telegram.org/bot[MASKED]'),
            (r'DATABASE_URL=[^\s]+', 'DATABASE_URL_MASKED'),
        ]
    
    def filter(self, record):
        try:
            # Handle the case where msg is a string
            if isinstance(record.msg, str):
                for pattern, mask in self.patterns:
                    record.msg = re.sub(pattern, mask, record.msg)
            
            # Handle the case where there are arguments
            if record.args:
                # Convert args to list if it's a tuple
                args = list(record.args)
                modified = False
                
                # Process each argument
                for i, arg in enumerate(args):
                    if isinstance(arg, str):
                        for pattern, mask in self.patterns:
                            new_arg = re.sub(pattern, mask, arg)
                            if new_arg != arg:
                                args[i] = new_arg
                                modified = True
                
                # Only update args if we made changes
                if modified:
                    record.args = tuple(args)
            
            # Handle the case where msg might be formatted with args
            if record.args:
                try:
                    # Try to create the formatted message
                    formatted_msg = record.msg % record.args
                    # Apply patterns to the formatted message
                    for pattern, mask in self.patterns:
                        formatted_msg = re.sub(pattern, mask, formatted_msg)
                    # Update the record
                    record.msg = formatted_msg
                    record.args = ()
                except (TypeError, ValueError):
                    # If formatting fails, just continue with original message
                    pass
            
        except Exception as e:
            # Log the error but don't block the message
            print(f"Error in SensitiveDataFilter: {e}")
        
        return True

def setup_logging():
    """Configure logging with appropriate levels for different components"""
    # Get config instance
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
    
    # Determine log directory based on environment
    if config.ENVIRONMENT == Environment.PRODUCTION:
        log_dir = Path('/var/log/tg-readlater-bot')
    else:
        log_dir = Path('logs')
    
    # Create log directory if it doesn't exist
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        print(f"Warning: Cannot create log directory in {log_dir}. Using current directory.")
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
    
    # Configure file handlers
    handlers = []
    try:
        # Bot log handler
        bot_log_path = log_dir / 'bot.log'
        bot_file_handler = logging.FileHandler(str(bot_log_path), mode='w')  # Use 'w' mode to start fresh
        bot_file_handler.setFormatter(formatter)
        handlers.append(bot_file_handler)
        
        # Error log handler
        error_log_path = log_dir / 'error.log'
        error_file_handler = logging.FileHandler(str(error_log_path), mode='w')  # Use 'w' mode to start fresh
        error_file_handler.setFormatter(formatter)
        error_file_handler.setLevel(logging.ERROR)
        handlers.append(error_file_handler)
        
    except PermissionError as e:
        print(f"Warning: Cannot create log files: {e}")
        # Continue with console logging only
        handlers = []
    
    # Create and add filter
    sensitive_filter = SensitiveDataFilter()
    
    # Set up root logger
    root_logger.setLevel(logging.INFO if not config.DEBUG else logging.DEBUG)
    
    # Add filter to root logger
    root_logger.addFilter(sensitive_filter)
    
    # Add handlers and filters
    for handler in handlers:
        handler.addFilter(sensitive_filter)
        root_logger.addHandler(handler)
    
    # Add console handler last
    console_handler.addFilter(sensitive_filter)
    root_logger.addHandler(console_handler)
    
    # Set specific component log levels
    if config.DEBUG:
        logging.getLogger('__main__').setLevel(logging.DEBUG)
        logging.getLogger('bot').setLevel(logging.DEBUG)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('telegram').setLevel(logging.INFO)
        logging.getLogger('apscheduler').setLevel(logging.INFO)
    else:
        for logger_name in ['httpx', 'telegram', 'apscheduler']:
            logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    # Log startup message
    logging.info(f"Logging setup completed. Environment: {config.ENVIRONMENT}, Using log directory: {log_dir}")