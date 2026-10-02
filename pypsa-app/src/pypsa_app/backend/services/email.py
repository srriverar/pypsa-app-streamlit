"""Email notification service using SMTP."""

import logging
import re
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTPAuthenticationError, SMTPServerDisconnected

from jinja2 import Environment, FileSystemLoader
from markupsafe import escape

from pypsa_app.backend.__version__ import __version__
from pypsa_app.backend.settings import settings

logger = logging.getLogger(__name__)

_SHORT_VERSION = re.sub(r"\.post\d+\.", ".", __version__).split("+")[0]

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=True,
)


def _render_html(
    subject: str,
    content: str,
    app_url: str,
    action_url: str | None = None,
    action_label: str | None = None,
) -> str:
    """Render the base email template with the given context."""
    template = _jinja_env.get_template("email.html.j2")
    return template.render(
        subject=subject,
        content=content,
        app_url=app_url,
        version=_SHORT_VERSION,
        action_url=action_url,
        action_label=action_label,
    )


def _build_message(
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
) -> EmailMessage:
    """Build a multipart email message with text and HTML alternatives."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"PyPSA App <{settings.smtp_from_address}>"
    msg["To"] = to
    msg.set_content(body_text)
    msg.add_alternative(body_html, subtype="html")
    return msg


def _smtp_send(msg: EmailMessage) -> None:
    """Open an SMTP connection and send a message."""
    if settings.smtp_port == 465:  # noqa: PLR2004
        server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10)
    else:
        server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)

    with server:
        if settings.smtp_port != 465 and settings.smtp_use_tls:  # noqa: PLR2004
            server.starttls()
        if settings.smtp_username and settings.smtp_password:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)


def _send_email(
    to: str,
    subject: str,
    body_html: str,
    body_text: str,
    max_retries: int = 2,
    retry_delay: int = 5,
) -> None:
    """Send an email via SMTP. Retries on transient failures."""
    if not settings.smtp_enabled:
        return

    msg = _build_message(to, subject, body_html, body_text)

    for attempt in range(max_retries + 1):
        try:
            _smtp_send(msg)
        except SMTPAuthenticationError:
            raise
        except (TimeoutError, SMTPServerDisconnected, OSError) as e:
            if attempt < max_retries:
                logger.info(
                    "Email to %s failed (attempt %d/%d: %s), retrying in %ds",
                    to,
                    attempt + 1,
                    max_retries + 1,
                    e,
                    retry_delay,
                )
                time.sleep(retry_delay)
            else:
                logger.warning(
                    "Failed to send email to %s: %s", to, subject, exc_info=True
                )
                return
        except Exception:
            logger.warning("Failed to send email to %s: %s", to, subject, exc_info=True)
            return
        else:
            logger.info("Email sent to %s: %s", to, subject)
            return


def _send_notification(
    to: str | list[str],
    subject: str,
    content: str,
    body_text: str,
    action_url: str | None = None,
    action_label: str | None = None,
) -> None:
    """Render HTML and send an email to one or more recipients."""
    body_html = _render_html(
        subject=subject,
        content=content,
        app_url=settings.base_url,
        action_url=action_url,
        action_label=action_label,
    )
    recipients = [to] if isinstance(to, str) else to
    for addr in recipients:
        _send_email(
            to=addr,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
        )


def send_account_approved_email(
    username: str,
    email: str | None,
) -> None:
    """Send an account-approved notification email."""
    if email is None:
        return

    safe_name = escape(username)
    _send_notification(
        to=email,
        subject="Your account has been approved",
        content=(
            f"<p>Hi {safe_name},</p>"
            f"<p>Your PyPSA App account has been approved. "
            f"You can now sign in and start using the application.</p>"
        ),
        body_text=(
            f"Hi {username},\n\n"
            f"Your PyPSA App account has been approved. "
            f"You can now sign in and start using the application.\n\n"
            f"Sign in at: {settings.base_url}\n\n"
        ),
        action_url=settings.base_url,
        action_label="Sign in",
    )


def send_new_user_pending_email(
    admin_emails: list[str],
    username: str,
) -> None:
    """Notify admins that a new user signed up and is awaiting approval."""
    if not admin_emails:
        return

    safe_name = escape(username)
    admin_url = f"{settings.base_url}/admin/users"
    _send_notification(
        to=admin_emails,
        subject="New user pending approval",
        content=(
            f"<p>A new user <strong>{safe_name}</strong> has signed up "
            f"and is waiting for approval.</p>"
            f"<p>Please review their account in the admin panel.</p>"
        ),
        body_text=(
            f"A new user '{username}' has signed up and is "
            f"waiting for approval.\n\n"
            f"Review pending users at: {admin_url}\n\n"
        ),
        action_url=admin_url,
        action_label="Review user",
    )
