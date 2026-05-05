import resend
from app.core.config import settings

resend.api_key = settings.RESEND_API_KEY


def _send(to: str, subject: str, html: str) -> None:
    """Send email via Resend. Raises on failure."""
    resend.Emails.send({
        "from": f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>",
        "to": [to],
        "subject": subject,
        "html": html,
    })


def send_verification_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/verify?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:40px 24px">
      <h2 style="font-size:24px;font-weight:700;margin-bottom:8px">Confirm your email</h2>
      <p style="color:#666;margin-bottom:32px">Click the button below to activate your DeepDigest account.</p>
      <a href="{link}"
         style="display:inline-block;padding:14px 28px;background:#E07B52;color:#fff;
                border-radius:10px;text-decoration:none;font-weight:600;font-size:15px">
        Confirm email →
      </a>
      <p style="color:#999;font-size:12px;margin-top:32px">Link expires in 24 hours.<br/>If you didn't sign up, ignore this email.</p>
    </div>
    """
    _send(to, "Confirm your DeepDigest account", html)


def send_password_reset_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:40px 24px">
      <h2 style="font-size:24px;font-weight:700;margin-bottom:8px">Reset your password</h2>
      <p style="color:#666;margin-bottom:32px">Click below to set a new password. Link expires in 1 hour.</p>
      <a href="{link}"
         style="display:inline-block;padding:14px 28px;background:#E07B52;color:#fff;
                border-radius:10px;text-decoration:none;font-weight:600;font-size:15px">
        Reset password →
      </a>
      <p style="color:#999;font-size:12px;margin-top:32px">If you didn't request this, ignore the email.</p>
    </div>
    """
    _send(to, "Reset your DeepDigest password", html)


def send_welcome_email(to: str) -> None:
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:0 auto;padding:40px 24px">
      <h2 style="font-size:24px;font-weight:700;margin-bottom:8px">Welcome to DeepDigest 🎉</h2>
      <p style="color:#666;margin-bottom:16px">Your account is confirmed. Your first digest arrives today.</p>
      <p style="color:#666;margin-bottom:32px">Connect your Telegram to start receiving digests:</p>
      <a href="https://t.me/deepdigest_bot"
         style="display:inline-block;padding:14px 28px;background:#E07B52;color:#fff;
                border-radius:10px;text-decoration:none;font-weight:600;font-size:15px">
        Open Telegram bot →
      </a>
    </div>
    """
    _send(to, "Welcome to DeepDigest!", html)
