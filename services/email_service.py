
import logging
import requests
from typing import Tuple
from flask import current_app

logger = logging.getLogger(__name__)


class EmailService:
    """Service to send transactional emails via Brevo API."""

    @classmethod
    def send_password_reset_email(
        cls, to_email: str, recipient_name: str, reset_url: str
    ) -> Tuple[bool, str]:

        config = current_app.config
        api_key = config.get("BREVO_API_KEY", "").strip()
        from_email = config.get("BREVO_FROM_EMAIL", "").strip()

        if not api_key or not from_email:
            logger.error("Brevo API configuration is missing.")
            return False, "Email service is not configured."

        subject = "AI Interview System - Password Reset Request"

        plain_body = f"""Hello {recipient_name},

We received a request to reset your password for your AI Interview System account.

Click the link below to choose a new password:
{reset_url}

This password reset link is valid for 30 minutes.

If you did not make this request, you can safely ignore this email.

Best regards,
The AI Interview System Team
"""

        html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{ font-family: Arial, sans-serif; background: #f8f9fa; padding: 24px; color: #212529; }}
.container {{ max-width: 560px; margin: auto; background: white; border-radius: 12px; overflow: hidden; border: 1px solid #e9ecef; }}
.header {{ background: linear-gradient(135deg, #0d6efd, #6610f2); color: white; padding: 28px; text-align: center; }}
.content {{ padding: 32px 28px; line-height: 1.6; }}
.btn {{ display: inline-block; background: #0d6efd; color: white !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; margin: 20px 0; }}
.link-box {{ background: #f8f9fa; padding: 12px; word-break: break-all; font-size: 12px; }}
.footer {{ padding: 20px; background: #f8f9fa; text-align: center; font-size: 12px; color: #6c757d; }}
</style>
</head>
<body>
<div class="container">
<div class="header">
<h2>AI INTERVIEW SYSTEM</h2>
<p>Automated Candidate Evaluation &amp; Analytics Platform</p>
</div>
<div class="content">
<p>Hello <strong>{recipient_name}</strong>,</p>
<p>We received a request to reset the password associated with your account ({to_email}).</p>
<p style="text-align:center">
<a href="{reset_url}" class="btn">Reset Your Password</a>
</p>
<p>This reset link will expire in 30 minutes.</p>
<p>If the button does not work, copy this URL into your browser:</p>
<div class="link-box">{reset_url}</div>
<p>If you did not request a password reset, you can ignore this email.</p>
</div>
<div class="footer">
AI Interview System — B.Tech Computer Science Minor Project.<br>
This is an automated notification; please do not reply.
</div>
</div>
</body>
</html>
"""

        try:
            response = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "sender": {
                        "name": "AI Interview System",
                        "email": from_email,
                    },
                    "to": [
                        {
                            "email": to_email,
                            "name": recipient_name,
                        }
                    ],
                    "subject": subject,
                    "htmlContent": html_body,
                    "textContent": plain_body,
                },
                timeout=20,
            )

            response.raise_for_status()

            logger.info("Password reset email sent to %s", to_email)
            return True, f"Password reset email sent to {to_email}."

        except requests.RequestException as e:
            logger.error("Brevo email delivery failed: %s", e)
            return False, "Email delivery failed. Please try again."
