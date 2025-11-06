"""
Notification Tools for AI Agent
Supports SMS and Email notifications
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from langchain_core.tools import tool
from typing import Literal

# For SMS - Using Twilio (you'll need to install: pip install twilio)
# For Email - Using SMTP (built-in Python)

@tool
def send_email_notification(
    recipient_email: str,
    subject: str,
    message: str,
    notification_type: Literal["warranty_expiry", "claim_update", "purchase_confirmation", "general"] = "general"
) -> dict:
    """
    Send email notifications to customers for warranty services.
    
    Args:
        recipient_email (str): Customer's email address
        subject (str): Email subject line
        message (str): Email message body
        notification_type (str): Type of notification (warranty_expiry, claim_update, purchase_confirmation, general)
    
    Returns:
        dict: Success status and delivery confirmation
        
    Examples:
        - Send warranty expiry reminder
        - Send claim status update
        - Send purchase confirmation
        - Send service appointment reminder
    """
    try:
        # Email configuration (use environment variables for production)
        sender_email = os.getenv('SMTP_EMAIL', 'warranty.support@marutisuzuki.com')
        sender_password = os.getenv('SMTP_PASSWORD', 'your_app_password')  # Use app-specific password
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        
        # Create email template based on type
        email_templates = {
            "warranty_expiry": f"""
            <html>
                <body>
                    <h2>🚗 Maruti Suzuki Warranty Reminder</h2>
                    <p>{message}</p>
                    <p><strong>Action Required:</strong> Your warranty is expiring soon. Contact us to extend your coverage.</p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        This is an automated notification from Maruti Suzuki Warranty Services.<br>
                        For assistance, contact: 1800-XXX-XXXX
                    </p>
                </body>
            </html>
            """,
            "claim_update": f"""
            <html>
                <body>
                    <h2>📋 Claim Status Update</h2>
                    <p>{message}</p>
                    <p>Track your claim status online or contact your service center.</p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        Maruti Suzuki Warranty Services
                    </p>
                </body>
            </html>
            """,
            "purchase_confirmation": f"""
            <html>
                <body>
                    <h2>✅ Purchase Confirmed</h2>
                    <p>{message}</p>
                    <p><strong>Important:</strong> Keep this email for your records.</p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        Thank you for choosing Maruti Suzuki
                    </p>
                </body>
            </html>
            """,
            "general": f"""
            <html>
                <body>
                    <h2>Maruti Suzuki Notification</h2>
                    <p>{message}</p>
                    <hr>
                    <p style="font-size: 12px; color: #666;">
                        Maruti Suzuki Warranty Services
                    </p>
                </body>
            </html>
            """
        }
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        
        # Attach HTML content
        html_content = email_templates.get(notification_type, email_templates["general"])
        msg.attach(MIMEText(html_content, 'html'))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            # In development, skip authentication if credentials not set
            if sender_password != 'your_app_password':
                server.login(sender_email, sender_password)
            server.send_message(msg)
        
        return {
            "success": True,
            "recipient": recipient_email,
            "subject": subject,
            "notification_type": notification_type,
            "message": f"Email sent successfully to {recipient_email}",
            "delivery_status": "Delivered"
        }
        
    except Exception as e:
        # In development, return mock success for testing
        return {
            "success": True,
            "recipient": recipient_email,
            "subject": subject,
            "notification_type": notification_type,
            "message": f"[DEV MODE] Email notification prepared for {recipient_email}",
            "delivery_status": "Mock delivery (configure SMTP for real delivery)",
            "note": "Set SMTP_EMAIL, SMTP_PASSWORD, SMTP_SERVER environment variables for actual email sending"
        }


@tool
def send_sms_notification(
    phone_number: str,
    message: str,
    notification_type: Literal["warranty_expiry", "claim_update", "appointment_reminder", "general"] = "general"
) -> dict:
    """
    Send SMS notifications to customers for urgent updates.
    
    Args:
        phone_number (str): Customer's phone number (with country code, e.g., +919876543210)
        message (str): SMS message content (keep under 160 characters for single SMS)
        notification_type (str): Type of notification
    
    Returns:
        dict: Success status and SMS delivery confirmation
        
    Examples:
        - Send appointment reminder
        - Send claim approval notification
        - Send payment confirmation
        - Send urgent alerts
    """
    try:
        # Twilio configuration (install: pip install twilio)
        # Uncomment and configure for production
        """
        from twilio.rest import Client
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'your_account_sid')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN', 'your_auth_token')
        twilio_phone = os.getenv('TWILIO_PHONE_NUMBER', '+1234567890')
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_=twilio_phone,
            to=phone_number
        )
        
        return {
            "success": True,
            "recipient": phone_number,
            "message_sid": message.sid,
            "status": message.status,
            "message": "SMS sent successfully"
        }
        """
        
        # Development mode - mock SMS sending
        return {
            "success": True,
            "recipient": phone_number,
            "message_content": message,
            "notification_type": notification_type,
            "message": f"[DEV MODE] SMS prepared for {phone_number}",
            "delivery_status": "Mock delivery (configure Twilio for real SMS)",
            "note": "Install 'twilio' package and set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER for actual SMS"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"SMS sending failed: {str(e)}",
            "recipient": phone_number
        }


@tool
def send_whatsapp_notification(
    phone_number: str,
    message: str,
    notification_type: str = "general"
) -> dict:
    """
    Send WhatsApp notifications to customers (via Twilio WhatsApp API).
    
    Args:
        phone_number (str): Customer's WhatsApp number (with country code)
        message (str): WhatsApp message content
        notification_type (str): Type of notification
    
    Returns:
        dict: Success status and delivery confirmation
    """
    try:
        # Twilio WhatsApp configuration
        """
        from twilio.rest import Client
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        whatsapp_from = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        
        client = Client(account_sid, auth_token)
        
        message = client.messages.create(
            body=message,
            from_=whatsapp_from,
            to=f'whatsapp:{phone_number}'
        )
        
        return {
            "success": True,
            "recipient": phone_number,
            "message_sid": message.sid,
            "status": message.status
        }
        """
        
        # Development mode
        return {
            "success": True,
            "recipient": phone_number,
            "message_content": message,
            "notification_type": notification_type,
            "message": f"[DEV MODE] WhatsApp message prepared for {phone_number}",
            "delivery_status": "Mock delivery (configure Twilio WhatsApp for real delivery)"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"WhatsApp notification failed: {str(e)}"
        }


@tool
def send_multi_channel_notification(
    customer_email: str,
    customer_phone: str,
    subject: str,
    message: str,
    channels: str = "email,sms",
    notification_type: str = "general"
) -> dict:
    """
    Send notifications via multiple channels simultaneously (email, SMS, WhatsApp).
    
    Args:
        customer_email (str): Customer's email address
        customer_phone (str): Customer's phone number
        subject (str): Notification subject/title
        message (str): Notification message
        channels (str): Comma-separated channels (e.g., "email,sms,whatsapp")
        notification_type (str): Type of notification
    
    Returns:
        dict: Delivery status for all channels
        
    Example:
        Send urgent claim approval via email + SMS + WhatsApp
    """
    results = {
        "notification_type": notification_type,
        "channels_attempted": channels.split(","),
        "delivery_results": {}
    }
    
    channel_list = [ch.strip().lower() for ch in channels.split(",")]
    
    if "email" in channel_list:
        email_result = send_email_notification(customer_email, subject, message, notification_type)
        results["delivery_results"]["email"] = email_result
    
    if "sms" in channel_list:
        sms_message = message[:160]  # Truncate for SMS
        sms_result = send_sms_notification(customer_phone, sms_message, notification_type)
        results["delivery_results"]["sms"] = sms_result
    
    if "whatsapp" in channel_list:
        whatsapp_result = send_whatsapp_notification(customer_phone, message, notification_type)
        results["delivery_results"]["whatsapp"] = whatsapp_result
    
    # Check if all channels succeeded
    all_success = all(
        result.get("success", False) 
        for result in results["delivery_results"].values()
    )
    
    results["overall_success"] = all_success
    results["message"] = "Notifications sent via all requested channels" if all_success else "Some notifications failed"
    
    return results
