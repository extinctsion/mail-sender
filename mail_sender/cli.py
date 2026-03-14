"""CLI interface for mail-sender."""

from __future__ import annotations

import asyncio
import json
import logging

import typer

from mail_sender.sender import send_message
from mail_sender.validator import MailSenderError

app = typer.Typer(name="mail-sender", help="Bulk email sender with Jinja2 templates.")


@app.command("send")
def send_cmd(
    env: str = typer.Option(".env", "--env", help="Path to .env file with SMTP credentials"),
    users: str = typer.Option("users.json", "--users", help="Path to users JSON file"),
    template: str = typer.Option("template.html", "--template", help="Path or built-in template name"),
    subject: str = typer.Option("Hello, {{name}}!", "--subject", help="Email subject (Jinja2 supported)"),
    delay: float = typer.Option(10.0, "--delay", help="Seconds to wait between sends"),
) -> None:
    """Send personalized bulk emails."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    try:
        result = asyncio.run(
            send_message(
                env_path=env,
                users_path=users,
                template_path=template,
                subject=subject,
                delay=delay,
            )
        )
    except MailSenderError as exc:
        typer.echo(f"Error: {exc}", err=True)
        if exc.details:
            for detail in exc.details:
                typer.echo(f"  - {detail}", err=True)
        raise typer.Exit(code=1)

    typer.echo(json.dumps(result, indent=2))

    if result["failed"] > 0:
        raise typer.Exit(code=1)


# Add a no-op callback so Typer treats "send" as a real subcommand
# instead of auto-simplifying to a single-command app
@app.callback()
def main() -> None:
    """Bulk email sender with Jinja2 templates."""


if __name__ == "__main__":
    app()
