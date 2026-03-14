"""Core email sending logic."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, TypedDict

import jinja2

from mail_sender.validator import SmtpConfig, User, resolve_template, validate_env_config, validate_users

logger = logging.getLogger("mail_sender")


class ErrorDetail(TypedDict):
    email: str
    error: str


class SendResult(TypedDict):
    success: int
    failed: int
    errors: list[ErrorDetail]


def _send_single_email(
    config: SmtpConfig,
    to_email: str,
    subject: str,
    html_body: str,
) -> None:
    """Send a single email via SMTP (blocking — run in a thread)."""
    msg = MIMEMultipart("alternative")
    msg["From"] = config.email_address
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    if config.port == 465:
        server = smtplib.SMTP_SSL(config.server, config.port)
    else:
        server = smtplib.SMTP(config.server, config.port)

    try:
        server.ehlo()
        if config.use_tls and config.port != 465:
            server.starttls()
            server.ehlo()
        server.login(config.email_address, config.password)
        server.send_message(msg)
    finally:
        server.quit()


async def send_message(
    *,
    env_path: str | Path = ".env",
    users_path: str | Path = "users.json",
    template_path: str | Path = "template.html",
    subject: str = "Hello, {{name}}!",
    delay: float = 10.0,
) -> SendResult:
    """Send personalized bulk emails.

    Args:
        env_path: Path to ``.env`` file with SMTP credentials.
        users_path: Path to JSON file containing user list.
        template_path: Path to an HTML template or name of a built-in template.
        subject: Email subject line (supports Jinja2 placeholders).
        delay: Seconds to wait between each email send.

    Returns:
        A dict with ``success``, ``failed``, and ``errors`` keys.

    Raises:
        ConfigError: If ``.env`` is missing or invalid.
        UsersFileError: If users JSON is malformed.
        TemplateError: If the template cannot be found.
    """
    # Pre-flight validation
    config = validate_env_config(env_path)
    users = validate_users(users_path)
    resolved_path = resolve_template(template_path)

    template_str = resolved_path.read_text(encoding="utf-8")
    env = jinja2.Environment(undefined=jinja2.Undefined)
    body_template = env.from_string(template_str)
    subject_template = env.from_string(subject)

    success = 0
    failed = 0
    errors: list[ErrorDetail] = []

    for idx, user in enumerate(users):
        user_vars: dict[str, Any] = {"name": user.name, "email": user.email}

        try:
            rendered_body = body_template.render(**user_vars)
            rendered_subject = subject_template.render(**user_vars)

            await asyncio.to_thread(
                _send_single_email,
                config,
                user.email,
                rendered_subject,
                rendered_body,
            )
            success += 1
            logger.info("Email sent to %s", user.email)
        except Exception as exc:
            failed += 1
            error_msg = str(exc)
            errors.append({"email": user.email, "error": error_msg})
            logger.error("Failed to send to %s: %s", user.email, error_msg)

        # Wait between sends (skip after last email)
        if idx < len(users) - 1:
            await asyncio.sleep(delay)

    return {"success": success, "failed": failed, "errors": errors}
