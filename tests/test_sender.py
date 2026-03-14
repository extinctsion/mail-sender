"""Tests for mail_sender.sender."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mail_sender.sender import send_message


@pytest.fixture()
def _setup_files(tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path):
    """Provide all three input files via existing fixtures."""
    return tmp_env_file, tmp_users_file, tmp_template_file


@pytest.mark.asyncio
class TestSendMessage:
    async def test_all_success(self, tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        with patch("mail_sender.sender.smtplib") as mock_smtp_mod:
            mock_server = MagicMock()
            mock_smtp_mod.SMTP.return_value = mock_server

            result = await send_message(
                env_path=tmp_env_file,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                delay=0,
            )

        assert result["success"] == 2
        assert result["failed"] == 0
        assert result["errors"] == []

    async def test_partial_failure(self, tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        import smtplib as real_smtplib

        with patch("mail_sender.sender.smtplib") as mock_smtp_mod:
            mock_server = MagicMock()
            mock_smtp_mod.SMTP.return_value = mock_server
            mock_smtp_mod.SMTP_SSL = MagicMock()
            # Fail on the first send_message call, succeed on the second
            mock_server.send_message.side_effect = [
                real_smtplib.SMTPException("auth failed"),
                None,
            ]

            result = await send_message(
                env_path=tmp_env_file,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                delay=0,
            )

        assert result["success"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["email"] == "alice@example.com"
        assert "auth failed" in result["errors"][0]["error"]

    async def test_all_fail(self, tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        import smtplib as real_smtplib

        with patch("mail_sender.sender.smtplib") as mock_smtp_mod:
            mock_server = MagicMock()
            mock_smtp_mod.SMTP.return_value = mock_server
            mock_server.send_message.side_effect = real_smtplib.SMTPException("down")

            result = await send_message(
                env_path=tmp_env_file,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                delay=0,
            )

        assert result["success"] == 0
        assert result["failed"] == 2

    async def test_template_rendering(self, tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        with patch("mail_sender.sender.smtplib") as mock_smtp_mod:
            mock_server = MagicMock()
            mock_smtp_mod.SMTP.return_value = mock_server

            await send_message(
                env_path=tmp_env_file,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                delay=0,
            )

        # Check that the first email body contains the rendered name
        first_call_msg = mock_server.send_message.call_args_list[0][0][0]
        html_body = first_call_msg.get_payload()[0].get_payload()
        assert "Alice" in html_body
        assert "alice@example.com" in html_body

    async def test_subject_rendering(self, tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        with patch("mail_sender.sender.smtplib") as mock_smtp_mod:
            mock_server = MagicMock()
            mock_smtp_mod.SMTP.return_value = mock_server

            await send_message(
                env_path=tmp_env_file,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                subject="Hi {{name}}",
                delay=0,
            )

        first_call_msg = mock_server.send_message.call_args_list[0][0][0]
        assert first_call_msg["Subject"] == "Hi Alice"

    async def test_tls_called(self, tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        with patch("mail_sender.sender.smtplib") as mock_smtp_mod:
            mock_server = MagicMock()
            mock_smtp_mod.SMTP.return_value = mock_server

            await send_message(
                env_path=tmp_env_file,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                delay=0,
            )

        mock_server.starttls.assert_called()

    async def test_ssl_port_465(self, tmp_path: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        env = tmp_path / ".env"
        env.write_text(
            "SMTP_SERVER=smtp.example.com\n"
            "SMTP_PORT=465\n"
            "EMAIL_ADDRESS=a@b.com\n"
            "EMAIL_PASSWORD=pass\n"
            "SMTP_TLS=true\n"
        )

        with patch("mail_sender.sender.smtplib") as mock_smtp_mod:
            mock_server = MagicMock()
            mock_smtp_mod.SMTP_SSL.return_value = mock_server

            await send_message(
                env_path=env,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                delay=0,
            )

        mock_smtp_mod.SMTP_SSL.assert_called_with("smtp.example.com", 465)
        mock_server.starttls.assert_not_called()

    async def test_delay_between_sends(self, tmp_env_file: Path, tmp_users_file: Path, tmp_template_file: Path) -> None:
        with (
            patch("mail_sender.sender.smtplib") as mock_smtp_mod,
            patch("mail_sender.sender.asyncio.sleep") as mock_sleep,
        ):
            mock_server = MagicMock()
            mock_smtp_mod.SMTP.return_value = mock_server

            await send_message(
                env_path=tmp_env_file,
                users_path=tmp_users_file,
                template_path=tmp_template_file,
                delay=5.0,
            )

        # 2 users → 1 sleep call between them
        assert mock_sleep.call_count == 1
        mock_sleep.assert_called_with(5.0)

    async def test_validation_errors_propagate(self, tmp_path: Path) -> None:
        from mail_sender.validator import ConfigError

        with pytest.raises(ConfigError):
            await send_message(
                env_path=tmp_path / "missing.env",
                users_path="users.json",
                template_path="template.html",
                delay=0,
            )
