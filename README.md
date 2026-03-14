# mail-senderpy

Bulk email sender with Jinja2 templates and CLI.

Send personalized emails to a list of users using any SMTP provider (Gmail, Outlook, AWS SES, SendGrid, etc.).

## Installation

```bash
pip install mail-senderpy
```

## Quick Start

### Python API

```python
from mail_senderpy import send_message

result = send_message(
    env_path=".env",
    users_path="users.json",
    template_path="template.html",
)

print(result)
# {"success": 18, "failed": 2, "errors": [{"email": "...", "error": "..."}]}
```

Or use `send_message_async` in an async context:

```python
from mail_senderpy import send_message_async

result = await send_message_async(
    env_path=".env",
    users_path="users.json",
    template_path="template.html",
)
```

### CLI

```bash
mail-senderpy send --env .env --users users.json --template template.html
```

Options:

| Flag         | Default              | Description                          |
|--------------|----------------------|--------------------------------------|
| `--env`      | `.env`               | Path to `.env` file                  |
| `--users`    | `users.json`         | Path to users JSON file              |
| `--template` | `template.html`      | Path or built-in template name       |
| `--subject`  | `Hello, {{name}}!`   | Email subject (Jinja2 supported)     |
| `--delay`    | `10.0`               | Seconds between sends                |

## Configuration

Create a `.env` file with your SMTP credentials:

```env
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_ADDRESS=your@email.com
EMAIL_PASSWORD=app_password
SMTP_TLS=true
```

All fields are required except `SMTP_TLS` (defaults to `true`).

## Users JSON Format

```json
[
  {"email": "user1@example.com", "name": "Rahul"},
  {"email": "user2@example.com", "name": "Priya"}
]
```

Each object's fields are available as Jinja2 template variables.

## Templates

### Custom Templates

Create an HTML file with Jinja2 placeholders:

```html
<h1>Hello {{ name }}!</h1>
<p>We're reaching out to you at {{ email }}.</p>
```

### Built-in Templates

Pass a built-in template name instead of a file path:

- `marketing_email.html` — promotional layout with CTA button
- `feedback_request.html` — feedback request with link
- `announcement.html` — announcement layout

```bash
mail-senderpy send --template marketing_email.html
```

## Return Value

```json
{
  "success": 18,
  "failed": 2,
  "errors": [
    {"email": "user@test.com", "error": "SMTP authentication failed"}
  ]
}
```

## Error Handling

The library validates all inputs before sending and raises descriptive errors:

- `ConfigError` — missing or invalid `.env` file
- `UsersFileError` — malformed JSON or invalid user entries
- `TemplateError` — template file not found

```python
from mail_senderpy import send_message, MailSenderError

try:
    result = send_message(env_path=".env", users_path="users.json", template_path="template.html")
except MailSenderError as e:
    print(f"Error: {e}")
    print(f"Details: {e.details}")
```

## License

MIT
