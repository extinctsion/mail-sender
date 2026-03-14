"""Input validation: .env config, users JSON, and template resolution."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class MailSenderError(Exception):
    """Base exception for all mail-sender errors."""

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        self.details = details or []
        super().__init__(message)


class ConfigError(MailSenderError):
    """Raised when .env configuration is invalid or missing."""


class UsersFileError(MailSenderError):
    """Raised when users JSON is malformed or contains invalid entries."""


class TemplateError(MailSenderError):
    """Raised when template cannot be found or rendered."""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SmtpConfig:
    server: str
    port: int
    email_address: str
    password: str
    use_tls: bool


@dataclass(frozen=True)
class User:
    email: str
    name: str


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_ENV_KEYS = ("SMTP_SERVER", "SMTP_PORT", "EMAIL_ADDRESS", "EMAIL_PASSWORD")
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
_TEMPLATES_DIR = Path(__file__).parent / "templates"

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def validate_env_config(env_path: str | Path) -> SmtpConfig:
    """Load and validate SMTP configuration from a ``.env`` file.

    Returns a :class:`SmtpConfig` on success.
    Raises :class:`ConfigError` if the file is missing or has invalid values.
    """
    env_path = Path(env_path)
    if not env_path.is_file():
        raise ConfigError(
            f"Environment file not found: {env_path}",
            details=[f"File does not exist: {env_path}"],
        )

    values = dotenv_values(env_path)
    errors: list[str] = []

    for key in _REQUIRED_ENV_KEYS:
        if not values.get(key):
            errors.append(f"Missing or empty required key: {key}")

    # Port validation
    port = 587
    raw_port = values.get("SMTP_PORT", "")
    if raw_port:
        try:
            port = int(raw_port)
        except ValueError:
            errors.append(f"SMTP_PORT must be an integer, got: {raw_port!r}")

    if errors:
        raise ConfigError(
            "Invalid SMTP configuration",
            details=errors,
        )

    # TLS parsing
    tls_raw = values.get("SMTP_TLS", "true").lower()
    use_tls = tls_raw in ("true", "1", "yes")

    return SmtpConfig(
        server=values["SMTP_SERVER"],  # type: ignore[arg-type]
        port=port,
        email_address=values["EMAIL_ADDRESS"],  # type: ignore[arg-type]
        password=values["EMAIL_PASSWORD"],  # type: ignore[arg-type]
        use_tls=use_tls,
    )


def validate_users(users_path: str | Path) -> list[User]:
    """Load and validate user list from a JSON file.

    Returns a list of :class:`User` on success.
    Raises :class:`UsersFileError` on any problem.
    """
    users_path = Path(users_path)
    if not users_path.is_file():
        raise UsersFileError(
            f"Users file not found: {users_path}",
            details=[f"File does not exist: {users_path}"],
        )

    try:
        raw: Any = json.loads(users_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise UsersFileError(
            f"Invalid JSON in {users_path}",
            details=[str(exc)],
        ) from exc

    if not isinstance(raw, list):
        raise UsersFileError(
            "Users file must contain a JSON array",
            details=[f"Expected a list, got {type(raw).__name__}"],
        )

    errors: list[str] = []
    users: list[User] = []

    for idx, entry in enumerate(raw):
        if not isinstance(entry, dict):
            errors.append(f"Entry {idx}: expected an object, got {type(entry).__name__}")
            continue

        email = entry.get("email")
        name = entry.get("name")

        if not email:
            errors.append(f"Entry {idx}: missing or empty 'email' field")
        elif not isinstance(email, str) or not _EMAIL_RE.match(email):
            errors.append(f"Entry {idx}: invalid email format: {email!r}")

        if not name:
            errors.append(f"Entry {idx}: missing or empty 'name' field")
        elif not isinstance(name, str):
            errors.append(f"Entry {idx}: 'name' must be a string")

        if not errors or (email and name and isinstance(email, str) and isinstance(name, str)):
            if email and name and isinstance(email, str) and isinstance(name, str) and _EMAIL_RE.match(email):
                users.append(User(email=email, name=name))

    if errors:
        raise UsersFileError(
            "Invalid entries in users file",
            details=errors,
        )

    return users


def resolve_template(template_path: str | Path) -> Path:
    """Resolve a template path.

    Checks the filesystem first; falls back to built-in templates.
    Raises :class:`TemplateError` if the template cannot be found.
    """
    path = Path(template_path)
    if path.is_file():
        return path

    # Try as a built-in template name
    builtin = _TEMPLATES_DIR / path.name
    if builtin.is_file():
        return builtin

    raise TemplateError(
        f"Template not found: {template_path}",
        details=[
            f"Not found on disk: {path}",
            f"Not a built-in template: {path.name}",
            f"Available built-in templates: {', '.join(p.name for p in _TEMPLATES_DIR.glob('*.html'))}",
        ],
    )
