"""Tests for mail_senderpy.validator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from mail_senderpy.validator import (
    ConfigError,
    SmtpConfig,
    TemplateError,
    User,
    UsersFileError,
    resolve_template,
    validate_env_config,
    validate_users,
)


# ── validate_env_config ─────────────────────────────────────────────────


class TestValidateEnvConfig:
    def test_valid(self, tmp_env_file: Path) -> None:
        config = validate_env_config(tmp_env_file)
        assert config == SmtpConfig(
            server="smtp.example.com",
            port=587,
            email_address="sender@example.com",
            password="secret",
            use_tls=True,
        )

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(ConfigError, match="not found"):
            validate_env_config(tmp_path / "missing.env")

    @pytest.mark.parametrize("missing_key", [
        "SMTP_SERVER", "SMTP_PORT", "EMAIL_ADDRESS", "EMAIL_PASSWORD",
    ])
    def test_missing_key(self, tmp_path: Path, missing_key: str) -> None:
        lines = {
            "SMTP_SERVER": "smtp.example.com",
            "SMTP_PORT": "587",
            "EMAIL_ADDRESS": "a@b.com",
            "EMAIL_PASSWORD": "pass",
        }
        del lines[missing_key]
        env = tmp_path / ".env"
        env.write_text("\n".join(f"{k}={v}" for k, v in lines.items()))
        with pytest.raises(ConfigError) as exc_info:
            validate_env_config(env)
        assert any(missing_key in d for d in exc_info.value.details)

    def test_invalid_port(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text(
            "SMTP_SERVER=smtp.example.com\n"
            "SMTP_PORT=abc\n"
            "EMAIL_ADDRESS=a@b.com\n"
            "EMAIL_PASSWORD=pass\n"
        )
        with pytest.raises(ConfigError) as exc_info:
            validate_env_config(env)
        assert any("SMTP_PORT" in d for d in exc_info.value.details)

    @pytest.mark.parametrize("tls_value,expected", [
        ("true", True),
        ("True", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("0", False),
        ("no", False),
    ])
    def test_tls_variants(self, tmp_path: Path, tls_value: str, expected: bool) -> None:
        env = tmp_path / ".env"
        env.write_text(
            "SMTP_SERVER=smtp.example.com\n"
            "SMTP_PORT=587\n"
            "EMAIL_ADDRESS=a@b.com\n"
            "EMAIL_PASSWORD=pass\n"
            f"SMTP_TLS={tls_value}\n"
        )
        config = validate_env_config(env)
        assert config.use_tls is expected


# ── validate_users ───────────────────────────────────────────────────────


class TestValidateUsers:
    def test_valid(self, tmp_users_file: Path) -> None:
        users = validate_users(tmp_users_file)
        assert users == [
            User(email="alice@example.com", name="Alice"),
            User(email="bob@example.com", name="Bob"),
        ]

    def test_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(UsersFileError, match="not found"):
            validate_users(tmp_path / "missing.json")

    def test_invalid_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("{not valid json")
        with pytest.raises(UsersFileError, match="Invalid JSON"):
            validate_users(f)

    def test_not_a_list(self, tmp_path: Path) -> None:
        f = tmp_path / "obj.json"
        f.write_text(json.dumps({"email": "a@b.com", "name": "A"}))
        with pytest.raises(UsersFileError, match="JSON array"):
            validate_users(f)

    def test_missing_email_field(self, tmp_path: Path) -> None:
        f = tmp_path / "users.json"
        f.write_text(json.dumps([{"name": "Alice"}]))
        with pytest.raises(UsersFileError) as exc_info:
            validate_users(f)
        assert any("email" in d for d in exc_info.value.details)

    def test_missing_name_field(self, tmp_path: Path) -> None:
        f = tmp_path / "users.json"
        f.write_text(json.dumps([{"email": "alice@example.com"}]))
        with pytest.raises(UsersFileError) as exc_info:
            validate_users(f)
        assert any("name" in d for d in exc_info.value.details)

    def test_invalid_email_format(self, tmp_path: Path) -> None:
        f = tmp_path / "users.json"
        f.write_text(json.dumps([{"email": "not-an-email", "name": "X"}]))
        with pytest.raises(UsersFileError) as exc_info:
            validate_users(f)
        assert any("invalid email" in d for d in exc_info.value.details)


# ── resolve_template ─────────────────────────────────────────────────────


class TestResolveTemplate:
    def test_custom_path(self, tmp_template_file: Path) -> None:
        assert resolve_template(tmp_template_file) == tmp_template_file

    def test_builtin_name(self) -> None:
        result = resolve_template("marketing_email.html")
        assert result.is_file()
        assert result.name == "marketing_email.html"

    def test_not_found(self) -> None:
        with pytest.raises(TemplateError, match="not found"):
            resolve_template("nonexistent_template_xyz.html")
