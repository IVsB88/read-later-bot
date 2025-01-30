import pytest
from datetime import datetime, timedelta
from utils.rate_limiter import RateLimiter
import time

@pytest.fixture
def rate_limiter():
    return RateLimiter()

def test_message_within_limit(rate_limiter):
    """Test that messages within limit are allowed"""
    user_id = 12345
    # Try 10 messages (should all be allowed)
    for i in range(10):
        is_allowed, message = rate_limiter.check_rate_limit(user_id, 'messages')
        assert is_allowed == True
        assert message == ""

def test_message_exceeds_limit(rate_limiter):
    """Test that exceeding message limit is blocked"""
    user_id = 12345
    # Send 10 messages (limit)
    for _ in range(10):
        rate_limiter.check_rate_limit(user_id, 'messages')
    
    # 11th message should be blocked
    is_allowed, message = rate_limiter.check_rate_limit(user_id, 'messages')
    assert is_allowed == False
    assert "Rate limit exceeded" in message

def test_links_within_limit(rate_limiter):
    """Test that links within limit are allowed"""
    user_id = 12345
    # Try 5 links (should all be allowed)
    for _ in range(5):
        is_allowed, message = rate_limiter.check_rate_limit(user_id, 'links')
        assert is_allowed == True
        assert message == ""

def test_links_exceeds_limit(rate_limiter):
    """Test that exceeding link limit is blocked"""
    user_id = 12345
    # Send 5 links (limit)
    for _ in range(5):
        rate_limiter.check_rate_limit(user_id, 'links')
    
    # 6th link should be blocked
    is_allowed, message = rate_limiter.check_rate_limit(user_id, 'links')
    assert is_allowed == False
    assert "Rate limit exceeded" in message

def test_different_users(rate_limiter):
    """Test that limits are applied separately for different users"""
    user1_id = 12345
    user2_id = 67890
    
    # User 1 hits message limit
    for _ in range(10):
        rate_limiter.check_rate_limit(user1_id, 'messages')
    
    # User 1 should be blocked
    is_allowed, _ = rate_limiter.check_rate_limit(user1_id, 'messages')
    assert is_allowed == False
    
    # User 2 should still be allowed
    is_allowed, _ = rate_limiter.check_rate_limit(user2_id, 'messages')
    assert is_allowed == True

def test_limit_reset_after_period(rate_limiter):
    """Test that limits reset after the specified period"""
    user_id = 12345
    
    # Hit the link limit
    for _ in range(5):
        rate_limiter.check_rate_limit(user_id, 'links')
    
    # Verify limit is hit
    is_allowed, _ = rate_limiter.check_rate_limit(user_id, 'links')
    assert is_allowed == False
    
    # Manually clean old entries (simulating time passage)
    now = datetime.now()
    old_time = now - timedelta(seconds=61)  # Just over the 60-second limit
    rate_limiter._limits[user_id]['links'] = [
        (old_time, count) for timestamp, count in rate_limiter._limits[user_id]['links']
    ]
    
    # Should be allowed again
    is_allowed, _ = rate_limiter.check_rate_limit(user_id, 'links')
    assert is_allowed == True

def test_independent_limits(rate_limiter):
    """Test that message and link limits are tracked independently"""
    user_id = 12345
    
    # Hit message limit
    for _ in range(10):
        rate_limiter.check_rate_limit(user_id, 'messages')
    
    # Messages should be blocked
    is_allowed, _ = rate_limiter.check_rate_limit(user_id, 'messages')
    assert is_allowed == False
    
    # Links should still be allowed
    is_allowed, _ = rate_limiter.check_rate_limit(user_id, 'links')
    assert is_allowed == True

def test_invalid_action_type(rate_limiter):
    """Test handling of invalid action types"""
    user_id = 12345
    # Should default to allowing the action
    is_allowed, _ = rate_limiter.check_rate_limit(user_id, 'invalid_action')
    assert is_allowed == True

def test_error_handling(rate_limiter):
    """Test error handling (forcing an error by modifying internal state)"""
    user_id = 12345
    # Corrupt internal state
    rate_limiter._limits[user_id] = None
    
    # Should default to allowing the action
    is_allowed, _ = rate_limiter.check_rate_limit(user_id, 'messages')
    assert is_allowed == True