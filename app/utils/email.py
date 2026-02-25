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

def send_restaurant_approval_email(email: str, restaurant_name: str, owner_name: str):
    """Send approval email to restaurant owner"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🎉 Restaurant Application Approved - {restaurant_name}"
        msg['From'] = f"Fuji Sakura <{settings.MAIL_FROM}>"
        msg['To'] = email
        
        # HTML content with Fuji Sakura branding
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #FF5722 0%, #FF7043 100%); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 28px; font-weight: bold; }}
                .content {{ padding: 40px 30px; }}
                .success-icon {{ font-size: 60px; text-align: center; margin-bottom: 20px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #FF5722 0%, #FF7043 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
                .highlight {{ background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FF5722; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌸 Fuji Sakura Food Delivery</h1>
                    <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Restaurant Partnership Program</p>
                </div>
                
                <div class="content">
                    <div class="success-icon">🎉</div>
                    
                    <h2 style="color: #FF5722; text-align: center; margin-bottom: 30px;">
                        Congratulations! Your Application is Approved
                    </h2>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        Dear {owner_name},
                    </p>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        We are excited to inform you that your restaurant partnership application for <strong>{restaurant_name}</strong> has been approved! 🎊
                    </p>
                    
                    <div class="highlight">
                        <h3 style="color: #FF5722; margin-top: 0;">What's Next?</h3>
                        <ul style="color: #333; line-height: 1.8;">
                            <li>📋 <strong>Restaurant Dashboard Access:</strong> Coming soon - you'll receive login credentials</li>
                            <li>🍽️ <strong>Menu Setup:</strong> Add your delicious dishes and set pricing</li>
                            <li>📱 <strong>Order Management:</strong> Start receiving and managing customer orders</li>
                            <li>📊 <strong>Analytics:</strong> Track your restaurant's performance</li>
                        </ul>
                    </div>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        Our team will contact you within 24-48 hours with detailed onboarding instructions and your restaurant dashboard access.
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3001/restaurant/apply" class="button">
                            Check Application Status
                        </a>
                    </div>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        Welcome to the Fuji Sakura family! We look forward to a successful partnership.
                    </p>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        Best regards,<br>
                        <strong>Fuji Sakura Partnership Team</strong><br>
                        📧 support@fujisakura.com<br>
                        📞 +1 (555) 123-4567
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2026 Fuji Sakura Food Delivery. All rights reserved.</p>
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        Congratulations! Your Restaurant Application is Approved
        
        Dear {owner_name},
        
        We are excited to inform you that your restaurant partnership application for {restaurant_name} has been approved!
      
        What's Next?
        - Restaurant Dashboard Access: Coming soon - you'll receive login credentials
        - Menu Setup: Add your delicious dishes and set pricing
        - Order Management: Start receiving and managing customer orders
        - Analytics: Track your restaurant's performance
      
        Our team will contact you within 24-48 hours with detailed onboarding instructions.
        
        Welcome to the Fuji Sakura family!
        
        Best regards,
        Fuji Sakura Partnership Team
        support@fujisakura.com
        """
        
        # Attach both versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Restaurant approval email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send restaurant approval email to {email}: {e}")
        return False

def send_restaurant_rejection_email(email: str, restaurant_name: str, owner_name: str, rejection_reason: str = ""):
    """Send rejection email to restaurant owner"""
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"Restaurant Application Update - {restaurant_name}"
        msg['From'] = f"Fuji Sakura <{settings.MAIL_FROM}>"
        msg['To'] = email
        
        # HTML content with Fuji Sakura branding
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Arial', sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
                .header {{ background: linear-gradient(135deg, #FF5722 0%, #FF7043 100%); padding: 30px; text-align: center; }}
                .header h1 {{ color: white; margin: 0; font-size: 28px; font-weight: bold; }}
                .content {{ padding: 40px 30px; }}
                .info-icon {{ font-size: 60px; text-align: center; margin-bottom: 20px; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #FF5722 0%, #FF7043 100%); color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; margin: 20px 0; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 14px; }}
                .highlight {{ background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FF5722; }}
                .reason-box {{ background-color: #fafafa; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e0e0e0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🌸 Fuji Sakura Food Delivery</h1>
                    <p style="color: white; margin: 10px 0 0 0; font-size: 16px;">Restaurant Partnership Program</p>
                </div>
                
                <div class="content">
                    <div class="info-icon">📋</div>
                    
                    <h2 style="color: #FF5722; text-align: center; margin-bottom: 30px;">
                        Application Status Update
                    </h2>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        Dear {owner_name},
                    </p>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        Thank you for your interest in partnering with Fuji Sakura Food Delivery for <strong>{restaurant_name}</strong>.
                    </p>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        After careful review, we are unable to approve your application at this time.
                    </p>
                    
                    {f'''
                    <div class="reason-box">
                        <h3 style="color: #FF5722; margin-top: 0;">Review Notes:</h3>
                        <p style="color: #333; line-height: 1.6; margin: 0;">{rejection_reason}</p>
                    </div>
                    ''' if rejection_reason else ''}
                    
                    <div class="highlight">
                        <h3 style="color: #FF5722; margin-top: 0;">What You Can Do:</h3>
                        <ul style="color: #333; line-height: 1.8;">
                            <li>📝 <strong>Review Requirements:</strong> Check our partnership requirements</li>
                            <li>🔄 <strong>Reapply:</strong> You can submit a new application after addressing any concerns</li>
                            <li>📞 <strong>Contact Us:</strong> Reach out for clarification on requirements</li>
                            <li>💬 <strong>Get Support:</strong> Our team is here to help you succeed</li>
                        </ul>
                    </div>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        We appreciate your interest in joining our platform and encourage you to reapply once you've addressed any requirements.
                    </p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:3001/restaurant/apply" class="button">
                            Submit New Application
                        </a>
                    </div>
                    
                    <p style="font-size: 16px; line-height: 1.6; color: #333;">
                        Best regards,<br>
                        <strong>Fuji Sakura Partnership Team</strong><br>
                        📧 support@fujisakura.com<br>
                        📞 +1 (555) 123-4567
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2026 Fuji Sakura Food Delivery. All rights reserved.</p>
                    <p>This is an automated message. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Plain text fallback
        text_content = f"""
        Restaurant Application Update
        
        Dear {owner_name},
        
        Thank you for your interest in partnering with Fuji Sakura Food Delivery for {restaurant_name}.
        
        After careful review, we are unable to approve your application at this time.
        
        {f'Review Notes: {rejection_reason}' if rejection_reason else ''}
        
        What You Can Do:
        - Review Requirements: Check our partnership requirements
        - Reapply: You can submit a new application after addressing any concerns
        - Contact Us: Reach out for clarification on requirements
        
        We appreciate your interest and encourage you to reapply once requirements are met.
        
        Best regards,
        Fuji Sakura Partnership Team
        support@fujisakura.com
        """
        
        # Attach both versions
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Send email
        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(msg)
        
        logger.info(f"✅ Restaurant rejection email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send restaurant rejection email to {email}: {e}")
        return False