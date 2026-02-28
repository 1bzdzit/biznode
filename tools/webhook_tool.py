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

Webhook Tool
==========
Tool for making HTTP requests/webhooks.
"""

import requests
from typing import Any, Dict, Optional
from tools.base import BaseTool


class WebhookTool(BaseTool):
    """Tool for making HTTP requests and webhooks."""
    
    name = "webhook"
    description = "Make HTTP requests to external APIs"
    category = "network"
    
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "URL to request"
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                "default": "GET"
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers"
            },
            "data": {
                "type": "object",
                "description": "Request body (JSON)"
            },
            "timeout": {
                "type": "integer",
                "default": 30,
                "description": "Request timeout in seconds"
            }
        },
        "required": ["url"]
    }
    
    def run(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict] = None,
        data: Optional[Dict] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make an HTTP request.
        
        Args:
            url: Target URL
            method: HTTP method
            headers: Request headers
            data: Request body
            timeout: Timeout in seconds
            
        Returns:
            Response data
        """
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                timeout=timeout
            )
            
            # Try to parse JSON
            try:
                response_data = response.json()
            except:
                response_data = response.text
            
            return {
                "success": True,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "data": response_data
            }
            
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "error": "Request timed out"
            }
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection failed"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class APITool(BaseTool):
    """Tool for calling specific APIs."""
    
    name = "api_call"
    description = "Call specific business APIs"
    category = "network"
    
    # Pre-configured API endpoints
    API_TEMPLATES = {
        "stripe_payment": {
            "url": "https://api.stripe.com/v1/payments",
            "method": "POST"
        },
        "weather": {
            "url": "https://api.weather.example.com/forecast",
            "method": "GET"
        }
    }
    
    def run(
        self,
        api_name: str,
        action: str = "get",
        params: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call a pre-configured API.
        
        Args:
            api_name: Name of the API
            action: Action to perform
            params: API parameters
            **kwargs: Additional arguments
            
        Returns:
            API response
        """
        if api_name not in self.API_TEMPLATES:
            return {
                "success": False,
                "error": f"API '{api_name}' not configured"
            }
        
        template = self.API_TEMPLATES[api_name]
        
        # Add API key from config
        headers = kwargs.get("headers", {})
        if api_name == "stripe":
            headers["Authorization"] = f"Bearer {kwargs.get('api_key', '')}"
        
        # Make request
        webhook = WebhookTool()
        return webhook.run(
            url=template["url"],
            method=template["method"],
            headers=headers,
            data=params
        )


class WebhookTriggerTool(BaseTool):
    """Tool for triggering webhooks."""
    
    name = "trigger_webhook"
    description = "Trigger a webhook with data"
    category = "network"
    
    def __init__(self):
        super().__init__()
        self._webhooks = {}
    
    def register_webhook(self, name: str, url: str, secret: str = ""):
        """Register a webhook endpoint."""
        self._webhooks[name] = {
            "url": url,
            "secret": secret
        }
    
    def run(
        self,
        webhook_name: str,
        payload: Dict,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Trigger a registered webhook.
        
        Args:
            webhook_name: Name of registered webhook
            payload: Data to send
            
        Returns:
            Result dictionary
        """
        if webhook_name not in self._webhooks:
            return {
                "success": False,
                "error": f"Webhook '{webhook_name}' not registered"
            }
        
        webhook = self._webhooks[webhook_name]
        
        # Add signature if secret is set
        headers = kwargs.get("headers", {})
        if webhook.get("secret"):
            import hmac
            import hashlib
            
            import json
            payload_str = json.dumps(payload)
            signature = hmac.new(
                webhook["secret"].encode(),
                payload_str.encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = signature
        
        tool = WebhookTool()
        return tool.run(
            url=webhook["url"],
            method="POST",
            headers=headers,
            data=payload
        )
