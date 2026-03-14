"""Tests for mail_sender.cli."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from mail_sender.cli import app
from mail_sender.validator import ConfigError

runner = CliRunner()


class TestCli:
    def test_send_success(self) -> None:
        mock_result = {"success": 2, "failed": 0, "errors": []}

        with patch("mail_sender.cli.send_message", new_callable=AsyncMock, return_value=mock_result):
            result = runner.invoke(app, [
                "send",
                "--env", "fake.env",
                "--users", "fake.json",
                "--template", "fake.html",
            ])

        assert result.exit_code == 0
        assert '"success": 2' in result.output

    def test_send_with_failures(self) -> None:
        mock_result = {
            "success": 1,
            "failed": 1,
            "errors": [{"email": "x@y.com", "error": "timeout"}],
        }

        with patch("mail_sender.cli.send_message", new_callable=AsyncMock, return_value=mock_result):
            result = runner.invoke(app, [
                "send",
                "--env", "fake.env",
                "--users", "fake.json",
                "--template", "fake.html",
            ])

        assert result.exit_code == 1

    def test_send_config_error(self) -> None:
        with patch(
            "mail_sender.cli.send_message",
            new_callable=AsyncMock,
            side_effect=ConfigError("bad config", details=["missing SMTP_SERVER"]),
        ):
            result = runner.invoke(app, [
                "send",
                "--env", "fake.env",
                "--users", "fake.json",
                "--template", "fake.html",
            ])

        assert result.exit_code == 1
        assert "bad config" in result.output
