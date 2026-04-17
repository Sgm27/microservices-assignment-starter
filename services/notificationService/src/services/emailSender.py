import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

logger = logging.getLogger(__name__)


def send_email(
    to: str,
    subject: str,
    body: str,
    mock: bool,
    user: str,
    password: str,
    host: str,
    port: int,
) -> tuple[bool, Optional[str]]:
    """Send an email and return (success, error_message).

    In mock mode, just log the message and return (True, None) without
    making any network calls. In real mode, attempt to deliver via SMTP
    (SMTP_SSL on port 465, otherwise STARTTLS). Any exception is caught
    and returned as (False, str(exc)) - this function never raises.
    """
    if mock:
        logger.info(
            "[MOCK EMAIL] to=%s subject=%s body=%s",
            to,
            subject,
            body,
        )
        return True, None

    try:
        message = MIMEMultipart()
        message["From"] = user
        message["To"] = to
        message["Subject"] = subject
        message.attach(MIMEText(body, "plain"))

        if int(port) == 465:
            with smtplib.SMTP_SSL(host, port, timeout=10) as server:
                if user:
                    server.login(user, password)
                server.sendmail(user, [to], message.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                if user:
                    server.login(user, password)
                server.sendmail(user, [to], message.as_string())
        return True, None
    except Exception as exc:  # noqa: BLE001 - we never raise back to caller
        logger.exception("send_email failed: %s", exc)
        return False, str(exc)
