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

Telegram Tool
============
Tool for sending Telegram messages.
"""

import os
import requests
from typing import Any, Dict, Optional
from tools.base import BaseTool


class TelegramTool(BaseTool):
    """Tool for sending Telegram messages."""
    
    name = "send_telegram"
    description = "Send messages via Telegram"
    category = "communication"
    
    parameters = {
        "type": "object",
        "properties": {
            "chat_id": {
                "type": "string",
                "description": "Telegram chat ID"
            },
            "message": {
                "type": "string",
                "description": "Message to send"
            },
            "parse_mode": {
                "type": "string",
                "default": "Markdown",
                "description": "Parse mode (Markdown or HTML)"
            },
            "reply_markup": {
                "type": "object",
                "description": "Inline keyboard markup"
            }
        },
        "required": ["chat_id", "message"]
    }
    
    def __init__(self):
        """Initialize the telegram tool."""
        super().__init__()
        self._config = {}
    
    def configure(self, config: Dict[str, Any]):
        """Configure telegram settings."""
        self._config = {
            "bot_token": config.get("bot_token", os.getenv("TELEGRAM_BOT_TOKEN", "")),
            "api_url": f"https://api.telegram.org/bot{config.get('bot_token', os.getenv('TELEGRAM_BOT_TOKEN', ''))}"
        }
    
    def _get_api_url(self) -> str:
        """Get Telegram API URL."""
        if self._config.get("api_url"):
            return self._config["api_url"]
        
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        return f"https://api.telegram.org/bot{token}"
    
    def run(
        self,
        chat_id: str,
        message: str,
        parse_mode: str = "Markdown",
        reply_markup: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Send a Telegram message.
        
        Args:
            chat_id: Target chat ID
            message: Message text
            parse_mode: Markdown or HTML
            reply_markup: Optional inline keyboard
            
        Returns:
            Result dictionary
        """
        api_url = self._get_api_url()
        
        if not api_url or "bot" not in api_url:
            return {
                "success": False,
                "error": "Telegram bot token not configured"
            }
        
        try:
            url = f"{api_url}/sendMessage"
            
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode
            }
            
            if reply_markup:
                data["reply_markup"] = reply_markup
            
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            if result.get("ok"):
                return {
                    "success": True,
                    "message_id": result["result"]["message_id"],
                    "chat_id": chat_id
                }
            else:
                return {
                    "success": False,
                    "error": result.get("description", "Unknown error")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_photo(
        self,
        chat_id: str,
        photo_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a photo."""
        api_url = self._get_api_url()
        
        try:
            url = f"{api_url}/sendPhoto"
            
            data = {
                "chat_id": chat_id,
                "photo": photo_url
            }
            
            if caption:
                data["caption"] = caption
            
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            return {
                "success": result.get("ok", False),
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_document(
        self,
        chat_id: str,
        document_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a document."""
        api_url = self._get_api_url()
        
        try:
            url = f"{api_url}/sendDocument"
            
            data = {
                "chat_id": chat_id,
                "document": document_url
            }
            
            if caption:
                data["caption"] = caption
            
            response = requests.post(url, json=data, timeout=30)
            result = response.json()
            
            return {
                "success": result.get("ok", False),
                "result": result
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def notify_owner(
        self,
        message: str,
        owner_telegram_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send notification to the owner.
        
        Args:
            message: Message to send
            owner_telegram_id: Owner's Telegram ID (optional, uses config)
            
        Returns:
            Result dictionary
        """
        chat_id = owner_telegram_id or os.getenv("OWNER_TELEGRAM_ID", "")
        
        if not chat_id:
            return {
                "success": False,
                "error": "Owner Telegram ID not configured"
            }
        
        return self.run(chat_id, message)
