import os, ssl, smtplib
from email.message import EmailMessage
from datetime import datetime
import certifi  # 使用 certifi 的 CA

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

SMTP_USER = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS")

FROM_NAME = os.getenv("FROM_NAME", "NDIS HR")
FROM_EMAIL = os.getenv("FROM_EMAIL") or SMTP_USER 
FRONTEND_LOGIN_URL = os.getenv("FRONTEND_LOGIN_URL", "http://127.0.0.1:8000/portal/login")

TLS_CONTEXT = ssl.create_default_context()
try:
    TLS_CONTEXT.load_verify_locations(certifi.where())
except Exception:
    pass

def send_invite_email(to_email: str, first_name: str | None, temp_password: str):
    if not (SMTP_USER and SMTP_PASS):
        print("[mailer] missing SMTP creds: set SMTP_USERNAME/SMTP_PASSWORD (or SMTP_USER/SMTP_PASS) in .env")
        return
    if not to_email:                 
        print("[mailer] missing recipient email") 
        return

    subject = "Your NDIS Candidate Portal Access"
    html = f"""
    <p>Hi {first_name or 'there'},</p>
    <p>Welcome! Your candidate account for the NDIS HR portal has been created.</p>
    <ol>
      <li><b>Access the system</b>: <a href="{FRONTEND_LOGIN_URL}">{FRONTEND_LOGIN_URL}</a></li>
      <li><b>Login details</b>: use your email <code>{to_email}</code> and the temporary password below.</li>
      <li><b>Complete your profile</b> and <b>upload pre-onboarding documents</b> (resume, photo, etc.).</li>
    </ol>
    <p><b>Temporary password:</b> <code>{temp_password}</code></p>
    <p>For security, please change your password after first login.</p>
    <p>— NDIS HR Team</p>
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"] = to_email
    msg.set_content("Please view this email in HTML.")
    msg.add_alternative(html, subtype="html")

    # 连接并发送（带超时 + TLS；支持 465/587）
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=TLS_CONTEXT, timeout=10) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls(context=TLS_CONTEXT)
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)

def _send_html_via_smtp(to_email: str, subject: str, html: str) -> None:
    if not to_email:
        raise ValueError("Missing recipient email")

    from_addr = FROM_EMAIL or SMTP_USER
    if not (SMTP_USER and SMTP_PASS and from_addr):
        raise RuntimeError("SMTP credentials not configured properly")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{FROM_NAME} <{from_addr}>"
    msg["To"] = to_email

    # 纯文本降级（部分客户端用）
    msg.set_content("Please view this email in HTML.")
    # HTML 正文
    msg.add_alternative(html, subtype="html")

    # 465: SMTPS；587: STARTTLS
    if SMTP_PORT == 465:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=TLS_CONTEXT, timeout=10) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
    else:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls(context=TLS_CONTEXT)
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)


def send_offer_email(
    to_email: str,
    candidate_name: str,
    offer_link: str,
    *,
    company_name: str | None = None,
    expire_at: datetime | None = None,
) -> None:
    company = company_name or os.getenv("COMPANY_NAME", "Your Company")
    subject = "Your Offer Letter – Review & Sign"

    expiry_html = ""
    if expire_at:
        try:
            expiry_html = f"<p><strong>Link expires:</strong> {expire_at.strftime('%d %b %Y')}</p>"
        except Exception:
            pass

    html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;line-height:1.6;color:#222;">
      <p>Dear {candidate_name},</p>
      <p>
        We are pleased to share your offer letter from <strong>{company}</strong>.
        Please review and sign it via the secure link below:
      </p>
      <p style="margin:20px 0;">
        <a href="{offer_link}"
           style="background:#0b5fff;color:#fff;text-decoration:none;padding:10px 16px;border-radius:6px;display:inline-block;">
           Review &amp; Sign Offer
        </a>
      </p>
      {expiry_html}
      <p>If you did not expect this email, you can safely ignore it.</p>
      <p>Regards,<br/>{FROM_NAME}</p>
    </div>
    """

    _send_html_via_smtp(to_email, subject, html)
