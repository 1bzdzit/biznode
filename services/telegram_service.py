"""
BizNode – Digital Business Operator
Copyright 2026 1BZ DZIT DAO LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at:

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

---

BizNode Telegram Service
=======================
Handles all Telegram bot interactions.
Telegram Channel = Control layer for BizNode.

This service supports:
- Public bot for users to interact
- Owner bot for admin commands
- Network bot for associate communications
"""

import os
import requests
from typing import Dict, Any, List, Optional
import json

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


class TelegramService:
    """Telegram bot service for BizNode."""
    
    def __init__(self, bot_token: str = None):
        self.bot_token = bot_token or TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def _make_request(self, method: str, data: Dict = None) -> Dict:
        """Make API request to Telegram."""
        if not self.bot_token:
            return {"ok": False, "error": "No bot token configured"}
        
        url = f"{self.api_url}/{method}"
        try:
            response = requests.post(url, json=data, timeout=30)
            return response.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def send_message(
        self, 
        chat_id: str, 
        text: str,
        parse_mode: str = "Markdown",
        reply_markup: Dict = None
    ) -> Dict:
        """
        Send a message to a chat.
        
        Args:
            chat_id: Target chat ID
            text: Message text
            parse_mode: Markdown or HTML
            reply_markup: Optional keyboard markup
        
        Returns:
            API response
        """
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        if reply_markup:
            data["reply_markup"] = reply_markup
        
        return self._make_request("sendMessage", data)
    
    def send_photo(
        self,
        chat_id: str,
        photo: str,
        caption: str = None
    ) -> Dict:
        """Send a photo to a chat."""
        data = {
            "chat_id": chat_id,
            "photo": photo
        }
        if caption:
            data["caption"] = caption
        
        return self._make_request("sendPhoto", data)
    
    def send_document(
        self,
        chat_id: str,
        document: str,
        caption: str = None
    ) -> Dict:
        """Send a document to a chat."""
        data = {
            "chat_id": chat_id,
            "document": document
        }
        if caption:
            data["caption"] = caption
        
        return self._make_request("sendDocument", data)
    
    def get_updates(self, offset: int = None, limit: int = 100) -> List[Dict]:
        """Get pending updates."""
        data = {"limit": limit}
        if offset:
            data["offset"] = offset
        
        result = self._make_request("getUpdates", data)
        return result.get("result", [])
    
    def get_me(self) -> Dict:
        """Get bot information."""
        return self._make_request("getMe")
    
    def set_webhook(self, webhook_url: str) -> Dict:
        """Set webhook for incoming updates."""
        return self._make_request("setWebhook", {"url": webhook_url})
    
    def delete_webhook(self) -> Dict:
        """Delete webhook."""
        return self._make_request("deleteWebhook")
    
    def answer_callback_query(
        self, 
        callback_query_id: str, 
        text: str = None,
        show_alert: bool = False
    ) -> Dict:
        """Answer a callback query."""
        data = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        data["show_alert"] = show_alert
        
        return self._make_request("answerCallbackQuery", data)


# === Message Templates ===

def format_business_card(business: Dict) -> str:
    """Format business info as a nice card."""
    return f"""
🏢 *{business.get('business_name', 'Unknown Business')}*

📋 Status: {business.get('status', 'active')}
🔗 Node ID: `{business.get('node_id', 'N/A')}`

📅 Registered: {business.get('created_at', 'N/A')}
"""


def format_lead_notification(lead: Dict) -> str:
    """Format lead info for owner notification."""
    return f"""
📢 *New Business Lead*

👤 Name: {lead.get('name', 'Unknown')}
🏢 Business: {lead.get('business', 'Not specified')}
📧 Contact: {lead.get('contact_info', 'Not provided')}

📝 Summary: {lead.get('summary', 'No summary')}
📍 Source: {lead.get('source', 'Unknown')}
"""


def format_approval_request(action: Dict) -> str:
    """Format owner approval request."""
    return f"""
⚠️ *Action Requires Approval*

🔖 Type: {action.get('action_type', 'Unknown')}
📊 Risk Level: {action.get('risk_level', 'low').upper()}

📄 Data: {json.dumps(action.get('data', {}), indent=2)}

Reply with *approve* or *reject*
"""


def format_network_intro(associate: Dict, lead: Dict) -> str:
    """Format network introduction message."""
    return f"""
🤝 *New Network Opportunity*

We've identified a potential partner for you!

📋 Lead: {lead.get('name', 'Unknown')} - {lead.get('business', '')}
🏢 Your Role: {associate.get('role', 'Partner')}

Would you like us to facilitate an introduction?
"""


# === Convenience Functions ===

def notify_owner(owner_telegram_id: str, message: str, reply_markup: Dict = None) -> Dict:
    """Send notification to owner."""
    service = TelegramService()
    return service.send_message(owner_telegram_id, message, reply_markup=reply_markup)


def send_to_user(chat_id: str, message: str) -> Dict:
    """Send message to a user."""
    service = TelegramService()
    return service.send_message(chat_id, message)


def broadcast_to_channel(channel_id: str, message: str) -> Dict:
    """Broadcast message to a channel."""
    service = TelegramService()
    return service.send_message(channel_id, message)


# === Inline Keyboards ===

def get_approval_keyboard(action_id: int) -> Dict:
    """Get inline keyboard for approval."""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve_{action_id}"},
                {"text": "❌ Reject", "callback_data": f"reject_{action_id}"}
            ]
        ]
    }


def get_main_menu_keyboard() -> Dict:
    """Get main menu keyboard."""
    return {
        "keyboard": [
            ["📋 My Business", "🔍 Search"],
            ["👥 Associates", "📊 Network"],
            ["⚙️ Settings", "❓ Help"]
        ],
        "resize_keyboard": True
    }


if __name__ == "__main__":
    # Test
    service = TelegramService()
    me = service.get_me()
    print(f"Bot info: {me}")
