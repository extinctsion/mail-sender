"""Shared test fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mail_senderpy.validator import SmtpConfig


@pytest.fixture()
def tmp_env_file(tmp_path: Path) -> Path:
    """Write a valid .env file and return its path."""
    env = tmp_path / ".env"
    env.write_text(
        "SMTP_SERVER=smtp.example.com\n"
        "SMTP_PORT=587\n"
        "EMAIL_ADDRESS=sender@example.com\n"
        "EMAIL_PASSWORD=secret\n"
        "SMTP_TLS=true\n"
    )
    return env


@pytest.fixture()
def tmp_users_file(tmp_path: Path) -> Path:
    """Write a valid users.json file and return its path."""
    users = tmp_path / "users.json"
    users.write_text(
        json.dumps([
            {"email": "alice@example.com", "name": "Alice"},
            {"email": "bob@example.com", "name": "Bob"},
        ])
    )
    return users


@pytest.fixture()
def tmp_template_file(tmp_path: Path) -> Path:
    """Write a minimal HTML template and return its path."""
    tpl = tmp_path / "template.html"
    tpl.write_text("<p>Hello {{ name }}, your email is {{ email }}.</p>")
    return tpl


@pytest.fixture()
def smtp_config() -> SmtpConfig:
    """Return a pre-built SmtpConfig for tests."""
    return SmtpConfig(
        server="smtp.example.com",
        port=587,
        email_address="sender@example.com",
        password="secret",
        use_tls=True,
    )
