from datetime import datetime, timedelta
from typing import Dict, Tuple, List
import logging

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self):
        # Store user limits: {user_id: {action_type: [(timestamp, count)]}}
        self._limits: Dict[int, Dict[str, List[Tuple[datetime, int]]]] = {}
        
        # Configure limits
        self.LIMITS = {
            'links': {'count': 5, 'period': 60},  # 5 links per 60 seconds
            'messages': {'count': 10, 'period': 60}  # 10 messages per 60 seconds
        }
    
    def _clean_old_entries(self, user_id: int, action_type: str) -> None:
        """Remove entries older than the limit period"""
        now = datetime.now()
        if user_id in self._limits and action_type in self._limits[user_id]:
            period = self.LIMITS[action_type]['period']
            self._limits[user_id][action_type] = [
                (ts, count) for ts, count in self._limits[user_id][action_type]
                if now - ts < timedelta(seconds=period)
            ]
    
    def check_rate_limit(self, user_id: int, action_type: str) -> Tuple[bool, str]:
        """
        Check if the action is within rate limits.
        Returns (is_allowed, error_message)
        """
        try:
            now = datetime.now()
            
            # Initialize user's limits if not exists
            if user_id not in self._limits:
                self._limits[user_id] = {}
            if action_type not in self._limits[user_id]:
                self._limits[user_id][action_type] = []
            
            # Clean old entries
            self._clean_old_entries(user_id, action_type)
            
            # Calculate current count within the period
            current_count = sum(count for _, count in self._limits[user_id][action_type])
            
            # Check if limit exceeded
            limit = self.LIMITS[action_type]['count']
            if current_count >= limit:
                period = self.LIMITS[action_type]['period']
                error_msg = f"Rate limit exceeded. Please wait a moment before sending more {action_type}."
                logger.warning(f"Rate limit exceeded for user {user_id} - {action_type}")
                return False, error_msg
            
            # Update counts
            self._limits[user_id][action_type].append((now, 1))
            return True, ""
            
        except Exception as e:
            logger.error(f"Error in rate limiter: {str(e)}")
            return True, ""  # Allow on error to prevent blocking legitimate users
    
    def log_action(self, user_id: int, action_type: str) -> None:
        """Log an action without checking limits"""
        try:
            now = datetime.now()
            if user_id not in self._limits:
                self._limits[user_id] = {}
            if action_type not in self._limits[user_id]:
                self._limits[user_id][action_type] = []
            
            self._clean_old_entries(user_id, action_type)
            self._limits[user_id][action_type].append((now, 1))
            
        except Exception as e:
            logger.error(f"Error logging action in rate limiter: {str(e)}")