import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from app.core import config
from app.core.config import STUDENT_INVITATION_EXPIRE_HOURS
from app.services.email.templates import (
    review_notification,
    review_notification_html,
    student_invitation,
    student_invitation_html,
)


logger = logging.getLogger(__name__)


class EmailNotConfigured(RuntimeError):
    pass


class EmailDeliveryError(RuntimeError):
    pass


def _configured_message(
    recipient: str,
    subject: str,
    body: str,
    html_body: str,
) -> EmailMessage:
    if not config.MAIL_FROM or not config.MAIL_SERVER:
        raise EmailNotConfigured("SMTP sender address and server must be configured.")
    if config.MAIL_USE_SSL and config.MAIL_USE_TLS:
        raise EmailNotConfigured("SMTP SSL and STARTTLS cannot both be enabled.")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr((config.MAIL_FROM_NAME, config.MAIL_FROM))
    message["To"] = recipient
    message.set_content(body)
    message.add_alternative(html_body, subtype="html")
    return message


def ensure_email_configured() -> None:
    if not config.MAIL_FROM or not config.MAIL_SERVER:
        raise EmailNotConfigured("SMTP sender address and server must be configured.")
    if config.MAIL_USE_SSL and config.MAIL_USE_TLS:
        raise EmailNotConfigured("SMTP SSL and STARTTLS cannot both be enabled.")
    if bool(config.MAIL_USERNAME) != bool(config.MAIL_PASSWORD):
        raise EmailNotConfigured(
            "Configure both SMTP username and password, or leave both empty."
        )


def _send_message(message: EmailMessage) -> None:
    context = ssl.create_default_context()
    if config.MAIL_USE_SSL:
        with smtplib.SMTP_SSL(
            config.MAIL_SERVER,
            config.MAIL_PORT,
            timeout=15,
            context=context,
        ) as client:
            if config.MAIL_USERNAME:
                client.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
            client.send_message(message)
        return

    with smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT, timeout=15) as client:
        if config.MAIL_USE_TLS:
            client.starttls(context=context)
        if config.MAIL_USERNAME:
            client.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
        client.send_message(message)


async def send_review_notification(
    recipient: str,
    student_name: str,
    item_title: str,
    decision: str,
    feedback: str | None,
) -> None:
    subject, body = review_notification(
        student_name, item_title, decision, feedback
    )
    html_body = review_notification_html(
        student_name, item_title, decision, feedback
    )
    message = _configured_message(recipient, subject, body, html_body)
    try:
        await asyncio.to_thread(_send_message, message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError("Could not deliver the review notification.") from error
    logger.info("Delivered VeriSphere review notification.")


async def send_student_invitation(
    recipient: str,
    student_name: str,
    invitation_url: str,
) -> None:
    ensure_email_configured()
    subject, body = student_invitation(
        student_name, invitation_url, STUDENT_INVITATION_EXPIRE_HOURS
    )
    html_body = student_invitation_html(
        student_name, invitation_url, STUDENT_INVITATION_EXPIRE_HOURS
    )
    message = _configured_message(recipient, subject, body, html_body)
    try:
        await asyncio.to_thread(_send_message, message)
    except (OSError, smtplib.SMTPException) as error:
        raise EmailDeliveryError("Could not deliver the student invitation.") from error
    logger.info("Delivered student invitation email.")


async def dispatch_review_notification(
    recipient: str,
    student_name: str,
    item_title: str,
    decision: str,
    feedback: str | None,
) -> None:
    try:
        await send_review_notification(
            recipient, student_name, item_title, decision, feedback
        )
    except EmailNotConfigured as error:
        logger.info("Review notification was not sent: %s", error)
    except EmailDeliveryError:
        logger.exception("Review notification delivery failed.")


async def dispatch_student_invitation(
    recipient: str,
    student_name: str,
    invitation_url: str,
) -> None:
    try:
        await send_student_invitation(recipient, student_name, invitation_url)
    except (EmailNotConfigured, EmailDeliveryError):
        logger.exception("Student invitation delivery failed.")
