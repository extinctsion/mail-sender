"""mail-senderpy: Async bulk email sender with Jinja2 templates and CLI."""

from mail_senderpy.sender import send_message, send_message_async
from mail_senderpy.validator import (
    ConfigError,
    MailSenderError,
    TemplateError,
    UsersFileError,
    validate_env_config,
    validate_users,
)

try:
    from importlib.metadata import version

    __version__ = version("mail-senderpy")
except Exception:
    __version__ = "0.0.0-dev"

__all__ = [
    "send_message",
    "send_message_async",
    "MailSenderError",
    "ConfigError",
    "UsersFileError",
    "TemplateError",
    "validate_env_config",
    "validate_users",
]
