# utils/admin_notifier.py
import os
import logging
import httpx
from urllib.parse import quote

logger = logging.getLogger(__name__)

class AdminNotifier:
    def __init__(self, bot_token, chat_id):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
    async def notify(self, message: str) -> bool:
        """
        Send notification to admin channel
        Returns True if successful, False otherwise
        """
        try:
            # URL encode the message
            encoded_message = quote(message)
            url = f"{self.base_url}?chat_id={self.chat_id}&text={encoded_message}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                return True
                
        except Exception as e:
            logger.error(f"Failed to send admin notification: {str(e)}")
            return False

    async def notify_new_user(self, username: str, user_id: int) -> None:
        """Send notification about new user"""
        message = f"👤 New User: @{username} (User ID: {user_id})"
        await self.notify(message)

    async def notify_saved_link(self, username: str, total_links: int) -> None:
        """Send notification about saved link"""
        message = f"🔗 Link Saved: @{username} (Total links: {total_links})"
        await self.notify(message)