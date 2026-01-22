"""
Email utilities for sending OTP and notifications
Uses Mailtrap for development email testing
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

# Set up logging
logger = logging.getLogger(__name__)

def send_otp_email(to_email: str, otp: str, user_name: str = "User") -> bool:
    """
    Send OTP verification email using Mailtrap
    If Mailtrap not configured, prints OTP to console
    """
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.warning("⚠️ Mailtrap credentials not configured.")
        print(f"\n{'='*60}")
        print(f"📧 EMAIL TO: {to_email}")
        print(f"👤 USER: {user_name}")
        print(f"🔐 OTP CODE: {otp}")
        print(f"⏰ EXPIRES: 10 minutes")
        print(f"{'='*60}\n")
        return True  # Return True so the flow continues

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Fuji Sakura <{settings.MAIL_FROM}>"
        msg['To'] = to_email
        msg['Subject'] = "Your Fuji Sakura Verification Code"

        # HTML email body
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
                    color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; 
                }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .otp-box {{ 
                    background: white; border: 2px solid #ff6b6b; border-radius: 8px; 
                    padding: 20px; text-align: center; margin: 20px 0; 
                }}
                .otp-code {{ 
                    font-size: 32px; font-weight: bold; color: #ff6b6b; 
                    letter-spacing: 8px; font-family: 'Courier New', monospace; 
                }}
                .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
                .warning {{ 
                    background: #fff3cd; border-left: 4px solid #ffc107; 
                    padding: 10px; margin: 15px 0; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌸 Fuji Sakura Verification</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>Welcome to Fuji Sakura! Use the verification code below to complete your registration:</p>
                    
                    <div class="otp-box">
                        <p style="margin: 0; color: #666; font-size: 14px;">Your Verification Code</p>
                        <div class="otp-code">{otp}</div>
                        <p style="margin: 10px 0 0 0; color: #666; font-size: 12px;">Valid for 10 minutes</p>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong> Never share this code with anyone. 
                        Fuji Sakura will never ask for your verification code.
                    </div>
                    
                    <p>If you didn't request this code, please ignore this email.</p>
                    <p>Best regards,<br><strong>Fuji Sakura Team</strong></p>
                </div>
                <div class="footer">
                    <p>This is an automated message, please do not reply to this email.</p>
                    <p>&copy; 2026 Fuji Sakura. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Plain text fallback
        text_body = f"""
        Hello {user_name},

        Your Fuji Sakura verification code is: {otp}

        This code will expire in 10 minutes.

        If you didn't request this code, please ignore this email.

        Best regards,
        Fuji Sakura Team
        """

        # Attach both versions
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send email via Mailtrap
        server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"✅ Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False

def send_password_reset_email(to_email: str, reset_token: str, user_name: str = "User") -> bool:
    """
    Send password reset email
    """
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.warning("⚠️ Mailtrap credentials not configured. Email not sent.")
        logger.info(f"🔑 Reset token for {to_email}: {reset_token}")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Fuji Sakura <{settings.MAIL_FROM}>"
        msg['To'] = to_email
        msg['Subject'] = "Password Reset Request - Fuji Sakura"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ 
                    background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%); 
                    color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; 
                }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .token-box {{ 
                    background: white; border: 2px solid #ff6b6b; border-radius: 8px; 
                    padding: 20px; text-align: center; margin: 20px 0; 
                }}
                .token-code {{ 
                    font-size: 32px; font-weight: bold; color: #ff6b6b; 
                    letter-spacing: 8px; font-family: 'Courier New', monospace; 
                }}
                .warning {{ 
                    background: #fff3cd; border-left: 4px solid #ffc107; 
                    padding: 10px; margin: 15px 0; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔒 Password Reset Request</h1>
                </div>
                <div class="content">
                    <p>Hello {user_name},</p>
                    <p>We received a request to reset your password for your Fuji Sakura account.</p>
                    
                    <div class="token-box">
                        <p style="margin: 0; color: #666; font-size: 14px;">Your Reset Code</p>
                        <div class="token-code">{reset_token}</div>
                        <p style="margin: 10px 0 0 0; color: #666; font-size: 12px;">Valid for 30 minutes</p>
                    </div>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong> If you didn't request this password reset, 
                        please ignore this email. Your password will remain unchanged.
                    </div>
                    
                    <p>Best regards,<br><strong>Fuji Sakura Team</strong></p>
                </div>
            </div>
        </body>
        </html>
        """

        text_body = f"""
        Password Reset Request - Fuji Sakura

        Hello {user_name},

        Your password reset code is: {reset_token}

        This code will expire in 30 minutes.

        If you didn't request this, please ignore this email.

        Best regards,
        Fuji Sakura Team
        """

        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT)
        server.starttls()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.send_message(msg)
        server.quit()

        logger.info(f"✅ Password reset email sent to {to_email}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to send reset email to {to_email}: {str(e)}")
        return False