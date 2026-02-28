"""
BizNode Email Service
===================
SMTP email service for owner and associate communications.

Supports:
- Owner notifications
- Lead notifications
- Associate network emails
- AI agent emails
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import json

# Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
AGENT_EMAIL = os.getenv("AGENT_EMAIL", "")


class EmailService:
    """Email service for BizNode communications."""
    
    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = None
    ):
        self.smtp_host = smtp_host or SMTP_HOST
        self.smtp_port = smtp_port or SMTP_PORT
        self.smtp_user = smtp_user or SMTP_USER
        self.smtp_password = smtp_password or SMTP_PASSWORD
        self.from_email = from_email or AGENT_EMAIL or smtp_user
    
    def _create_message(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: str = None
    ) -> MIMEMultipart:
        """Create email message."""
        msg = MIMEMultipart('alternative')
        msg['From'] = self.from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Plain text part
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # HTML part if provided
        if html:
            html_part = MIMEText(html, 'html')
            msg.attach(html_part)
        
        return msg
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html: str = None,
        cc: str = None
    ) -> Dict[str, Any]:
        """
        Send an email.
        
        Args:
            to_email: Recipient email
            subject: Email subject
            body: Plain text body
            html: Optional HTML body
            cc: Optional CC recipients
        
        Returns:
            Success status and message
        """
        if not self.smtp_user or not self.smtp_password:
            return {
                "success": False,
                "error": "SMTP not configured"
            }
        
        try:
            msg = self._create_message(to_email, subject, body, html)
            
            if cc:
                msg['Cc'] = cc
            
            # Connect to SMTP server
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            
            # Send
            recipients = [to_email]
            if cc:
                recipients.append(cc)
            
            server.sendmail(self.from_email, recipients, msg.as_string())
            server.quit()
            
            return {
                "success": True,
                "message": f"Email sent to {to_email}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def send_html_email(
        self,
        to_email: str,
        subject: str,
        html_content: str
    ) -> Dict[str, Any]:
        """Send HTML email."""
        return self.send_email(
            to_email=to_email,
            subject=subject,
            body="Please enable HTML to view this email.",
            html=html_content
        )


# === Email Templates ===

def format_lead_notification_email(lead: Dict) -> tuple:
    """Format lead notification email."""
    subject = "🔔 New Business Lead - Action Required"
    
    body = f"""
New Business Lead Received
========================

Name: {lead.get('name', 'Unknown')}
Business: {lead.get('business', 'Not specified')}
Contact: {lead.get('contact_info', 'Not provided')}

Summary:
{lead.get('summary', 'No summary available')}

Source: {lead.get('source', 'Unknown')}

Please log in to review and take action.
"""
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
        .header {{ background: #4F46E5; color: white; padding: 20px; }}
        .content {{ padding: 20px; background: #f9f9f9; }}
        .label {{ font-weight: bold; color: #374151; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🔔 New Business Lead</h2>
    </div>
    <div class="content">
        <p><span class="label">Name:</span> {lead.get('name', 'Unknown')}</p>
        <p><span class="label">Business:</span> {lead.get('business', 'Not specified')}</p>
        <p><span class="label">Contact:</span> {lead.get('contact_info', 'Not provided')}</p>
        <p><span class="label">Summary:</span><br>{lead.get('summary', 'No summary')}</p>
        <p><span class="label">Source:</span> {lead.get('source', 'Unknown')}</p>
    </div>
</body>
</html>
"""
    
    return subject, body, html


def format_approval_request_email(action: Dict) -> tuple:
    """Format approval request email."""
    subject = "⚠️ Action Requires Your Approval"
    
    body = f"""
Approval Request
================

Type: {action.get('action_type', 'Unknown')}
Risk Level: {action.get('risk_level', 'low').upper()}

Data:
{json.dumps(action.get('data', {}), indent=2)}

Please respond with APPROVE or REJECT via Telegram.
"""
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; }}
        .warning {{ background: #FEF3C7; padding: 20px; border-left: 4px solid #F59E0B; }}
    </style>
</head>
<body>
    <div class="warning">
        <h2>⚠️ Approval Required</h2>
        <p><strong>Type:</strong> {action.get('action_type')}</p>
        <p><strong>Risk Level:</strong> {action.get('risk_level', 'low').upper()}</p>
        <p><strong>Data:</strong> {json.dumps(action.get('data', {}))}</p>
    </div>
    <p>Please respond via Telegram.</p>
</body>
</html>
"""
    
    return subject, body, html


def format_network_intro_email(associate: Dict, lead: Dict) -> tuple:
    """Format network introduction email."""
    subject = "🤝 Network Opportunity - Introduction Request"
    
    body = f"""
Network Opportunity
==================

A new lead has been identified that matches your profile.

Lead: {lead.get('name', 'Unknown')}
Business: {lead.get('business', '')}

Your Role: {associate.get('role', 'Partner')}

Would you like us to facilitate an introduction?
Reply via Telegram to proceed.
"""
    
    return subject, body, None


# === Convenience Functions ===

def notify_owner_email(owner_email: str, lead: Dict) -> Dict:
    """Send lead notification to owner."""
    service = EmailService()
    subject, body, html = format_lead_notification_email(lead)
    return service.send_email(owner_email, subject, body, html)


def send_approval_request(owner_email: str, action: Dict) -> Dict:
    """Send approval request to owner."""
    service = EmailService()
    subject, body, html = format_approval_request_email(action)
    return service.send_email(owner_email, subject, body, html)


def send_agent_email(
    to_email: str,
    subject: str,
    body: str,
    html: str = None
) -> Dict:
    """
    Send email from AI agent email address.
    This email belongs to AI, not owner.
    """
    service = EmailService()
    return service.send_email(to_email, subject, body, html)


# === Initialize ===

def init_email_service() -> EmailService:
    """Initialize email service with config."""
    return EmailService()


if __name__ == "__main__":
    service = init_email_service()
    print(f"SMTP Configured: {service.smtp_host}:{service.smtp_port}")
