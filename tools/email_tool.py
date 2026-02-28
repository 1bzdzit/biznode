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

Email Tool
=========
Tool for sending emails via SMTP.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, Optional
from tools.base import BaseTool


class EmailTool(BaseTool):
    """Tool for sending emails."""
    
    name = "send_email"
    description = "Send emails via SMTP"
    category = "communication"
    
    parameters = {
        "type": "object",
        "properties": {
            "to": {
                "type": "string",
                "description": "Recipient email address"
            },
            "subject": {
                "type": "string",
                "description": "Email subject"
            },
            "body": {
                "type": "string",
                "description": "Email body content"
            },
            "html": {
                "type": "boolean",
                "default": False,
                "description": "Send as HTML email"
            },
            "cc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CC recipients"
            },
            "bcc": {
                "type": "array",
                "items": {"type": "string"},
                "description": "BCC recipients"
            }
        },
        "required": ["to", "subject", "body"]
    }
    
    def __init__(self):
        """Initialize the email tool."""
        super().__init__()
        self._config = {}
    
    def configure(self, config: Dict[str, Any]):
        """Configure SMTP settings."""
        self._config = {
            "smtp_host": config.get("smtp_host", os.getenv("SMTP_HOST", "smtp.gmail.com")),
            "smtp_port": config.get("smtp_port", int(os.getenv("SMTP_PORT", "587"))),
            "smtp_user": config.get("smtp_user", os.getenv("SMTP_USER", "")),
            "smtp_password": config.get("smtp_password", os.getenv("SMTP_PASSWORD", "")),
            "from_email": config.get("from_email", os.getenv("AGENT_EMAIL", ""))
        }
    
    def run(
        self,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
        cc: Optional[list] = None,
        bcc: Optional[list] = None
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            html: Whether to send as HTML
            cc: CC recipients
            bcc: BCC recipients
            
        Returns:
            Result dictionary
        """
        if not self._config.get("smtp_user") or not self._config.get("smtp_password"):
            return {
                "success": False,
                "error": "SMTP not configured. Set SMTP_USER and SMTP_PASSWORD."
            }
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self._config.get("from_email") or self._config["smtp_user"]
            msg['To'] = to
            
            if cc:
                msg['Cc'] = ", ".join(cc)
            if bcc:
                msg['Bcc'] = ", ".join(bcc)
            
            # Attach body
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type))
            
            # Send email
            with smtplib.SMTP(
                self._config["smtp_host"],
                self._config["smtp_port"]
            ) as server:
                server.starttls()
                server.login(
                    self._config["smtp_user"],
                    self._config["smtp_password"]
                )
                
                recipients = [to]
                if cc:
                    recipients.extend(cc)
                if bcc:
                    recipients.extend(bcc)
                
                server.send_message(msg, to_addrs=recipients)
            
            return {
                "success": True,
                "to": to,
                "subject": subject
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_template(
        self,
        to: str,
        template_name: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send an email using a template.
        
        Args:
            to: Recipient email
            template_name: Name of template to use
            **kwargs: Template variables
            
        Returns:
            Result dictionary
        """
        # Simple template system
        templates = {
            "welcome": {
                "subject": "Welcome to {business_name}!",
                "body": "Hello {name},\n\nWelcome to {business_name}! We're excited to have you.\n\nBest,\nThe {business_name} Team"
            },
            "reminder": {
                "subject": "Reminder: {subject}",
                "body": "Hello {name},\n\nThis is a reminder about {subject}.\n\n{message}\n\nBest,\nThe Team"
            },
            "followup": {
                "subject": "Following up: {subject}",
                "body": "Hello {name},\n\n{message}\n\nBest,\nThe Team"
            }
        }
        
        if template_name not in templates:
            return {
                "success": False,
                "error": f"Template '{template_name}' not found"
            }
        
        template = templates[template_name]
        
        try:
            subject = template["subject"].format(**kwargs)
            body = template["body"].format(**kwargs)
        except KeyError as e:
            return {
                "success": False,
                "error": f"Missing template variable: {e}"
            }
        
        return self.run(to, subject, body)


class EmailReminderTool(BaseTool):
    """Tool for sending reminder emails."""
    
    name = "send_reminder"
    description = "Send a reminder email"
    category = "communication"
    
    def run(
        self,
        to: str,
        reminder_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a reminder email.
        
        Args:
            to: Recipient email
            reminder_type: Type of reminder
            **kwargs: Reminder details
            
        Returns:
            Result dictionary
        """
        email_tool = EmailTool()
        
        templates = {
            "invoice_overdue": {
                "subject": f"Invoice Overdue: {kwargs.get('invoice_number', '')}",
                "body": f"""Dear {kwargs.get('customer_name', 'Valued Customer')},

This is a friendly reminder that Invoice #{kwargs.get('invoice_number', '')} for ${kwargs.get('amount', '0.00')} was due on {kwargs.get('due_date', 'the due date')}.

Please let us know if you have any questions.

Best regards,
{kwargs.get('business_name', 'Your Business')}
"""
            },
            "meeting_reminder": {
                "subject": f"Meeting Reminder: {kwargs.get('meeting_title', '')}",
                "body": f"""Dear {kwargs.get('attendee_name', 'Valued Client')},

This is a reminder about our upcoming meeting:

Title: {kwargs.get('meeting_title', '')}
Date: {kwargs.get('meeting_date', '')}
Time: {kwargs.get('meeting_time', '')}
Location: {kwargs.get('meeting_location', 'TBD')}

{kwargs.get('additional_notes', '')}

Best regards,
{kwargs.get('business_name', 'Your Business')}
"""
            },
            "followup": {
                "subject": f"Following up: {kwargs.get('subject', 'Your Inquiry')}",
                "body": f"""Dear {kwargs.get('recipient_name', 'Valued Contact')},

{kwargs.get('message', 'Just wanted to follow up on our previous conversation.')}

Please don't hesitate to reach out if you have any questions.

Best regards,
{kwargs.get('business_name', 'Your Business')}
"""
            }
        }
        
        if reminder_type not in templates:
            return {
                "success": False,
                "error": f"Unknown reminder type: {reminder_type}"
            }
        
        template = templates[reminder_type]
        return email_tool.run(to, template["subject"], template["body"])
