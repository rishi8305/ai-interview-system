import logging
import requests
from typing import Tuple
from flask import current_app

logger = logging.getLogger(__name__)


class EmailService:
    """Service to send transactional emails (e.g., password reset) via Resend API."""

    @classmethod
    def send_password_reset_email(cls, to_email: str, recipient_name: str, reset_url: str) -> Tuple[bool, str]:
        """
        Send a password reset email to a registered user.
        Returns: (success: bool, status_message: str)
        """
        config = current_app.config
        api_key = config.get("RESEND_API_KEY", "").strip()
        from_email = config.get("RESEND_FROM_EMAIL", "").strip()

        if not api_key or not from_email:
            logger.error("Resend API configuration is missing.")
            return False, "Email service is not configured."

        # Build email content
        subject = "AI Interview System - Password Reset Request"
        
        # Plain text version
        plain_body = f"""Hello {recipient_name},

We received a request to reset your password for your AI Interview System account.

Click the link below (or copy and paste it into your browser) to choose a new password:
{reset_url}

This password reset link is valid for 30 minutes.

If you did not make this request, you can safely ignore this email. Your password will remain unchanged.

Best regards,
The AI Interview System Team
"""

        # HTML formatted version
        html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f9fa; margin: 0; padding: 24px; color: #212529; }}
    .container {{ max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08); border: 1px solid #e9ecef; }}
    .header {{ background: linear-gradient(135deg, #0d6efd 0%, #6610f2 100%); color: #ffffff; padding: 28px; text-align: center; }}
    .header h2 {{ margin: 0 0 6px 0; font-size: 22px; font-weight: 700; }}
    .header p {{ margin: 0; opacity: 0.85; font-size: 13px; }}
    .content {{ padding: 32px 28px; line-height: 1.6; font-size: 15px; }}
    .btn {{ display: inline-block; background: #0d6efd; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 600; font-size: 15px; margin: 20px 0; }}
    .link-box {{ background: #f8f9fa; padding: 12px; border-radius: 6px; font-family: monospace; font-size: 12px; word-break: break-all; color: #495057; border: 1px solid #dee2e6; margin-top: 15px; }}
    .footer {{ padding: 20px 28px; background: #f8f9fa; border-top: 1px solid #e9ecef; font-size: 12px; color: #6c757d; text-align: center; }}
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
      <p>We received a request to reset the password associated with your account (<strong>{to_email}</strong>).</p>
      <p style="text-align: center;">
        <a href="{reset_url}" class="btn" target="_blank">Reset Your Password</a>
      </p>
      <p style="font-size: 13px; color: #6c757d;">
        This reset link will automatically expire in <strong>30 minutes</strong> for your security.
      </p>
      <p style="font-size: 13px; color: #6c757d;">
        If the button above does not work, copy and paste this URL into your browser:
      </p>
      <div class="link-box">{reset_url}</div>
      <p style="font-size: 13px; color: #6c757d; margin-top: 24px;">
        If you did not request a password reset, no action is needed — your account remains completely secure.
      </p>
    </div>
    <div class="footer">
      &copy; AI Interview System &mdash; B.Tech Computer Science Minor Project.<br>
      This is an automated system notification; please do not reply directly to this email.
    </div>
  </div>
</body>
</html>
"""


        try:
            response = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": from_email,
                    "to": [to_email],
                    "subject": subject,
                    "html": html_body,
                    "text": plain_body,
                },
                timeout=20,
            )

            response.raise_for_status()

            logger.info(f"Password reset email sent to {to_email}")
            return True, f"Password reset email sent to {to_email}."

        except requests.RequestException as e:
            logger.error(f"Resend email delivery failed: {e}")
            return False, "Email delivery failed. Please try again."
