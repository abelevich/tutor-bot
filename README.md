# Voxara Bot

A multilingual language tutor Telegram bot powered by Claude. Currently supports English, with an architecture designed to easily add more languages.

## How it works

Send the bot a message in the language you're learning. It will:
1. Reply naturally, continuing the conversation like a patient friend
2. Correct any mistakes with explanations, categorized by severity (critical / grammar / style)
3. Relate corrections to common patterns for your native language

## Setup

### 1. Create a Telegram bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram and create a new bot. Save the token.

### 2. Get an Anthropic API key

Sign up at [console.anthropic.com](https://console.anthropic.com) and create an API key.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your tokens:
#   TELEGRAM_BOT_TOKEN=your-bot-token
#   ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Install dependencies

```bash
pip install -e .
```

### 5. Run the bot

```bash
# Polling mode (local development)
python -m src.main

# Webhook mode (production)
BOT_MODE=webhook TELEGRAM_WEBHOOK_URL=https://your-domain.com/webhook python -m src.main
```

## Webhook via Cloudflare Tunnel (production)

Recommended production setup when hosting on a machine without a public IP (e.g. a home Mac mini). [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/) opens an outbound connection to Cloudflare and routes inbound HTTPS traffic for your domain to a local port. No port forwarding, dynamic-DNS, or manual TLS certificates.

Prerequisites: a domain on Cloudflare (DNS managed by Cloudflare).

### 1. Install and register cloudflared

```bash
# macOS
brew install cloudflared

# authenticate; opens browser, pick your zone
cloudflared tunnel login

# create a named tunnel
cloudflared tunnel create voxara

# create the public DNS record: bot.your-domain.com -> tunnel
cloudflared tunnel route dns voxara bot.your-domain.com
```

### 2. Configure the tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: voxara
credentials-file: /Users/YOU/.cloudflared/<UUID>.json  # printed by `tunnel create`

ingress:
  - hostname: bot.your-domain.com
    service: http://127.0.0.1:8443
  - service: http_status:404
```

Use `127.0.0.1`, not `localhost`: the bot listens on IPv4 only, and `localhost` can resolve to `::1` first.

Smoke-test in the foreground: `cloudflared tunnel run voxara`.

### 3. Configure the bot

In `.env`:

```dotenv
BOT_MODE=webhook
TELEGRAM_WEBHOOK_URL=https://bot.your-domain.com/webhook
TELEGRAM_WEBHOOK_SECRET=<openssl rand -hex 32>
DATABASE_PATH=/absolute/path/to/voxara-bot/data/tutor.db
```

Set a real `TELEGRAM_WEBHOOK_SECRET`; if empty, forged webhook requests won't be rejected. Use an absolute `DATABASE_PATH` so it works regardless of the process's working directory.

Install into a virtualenv with Python 3.11+ (the macOS system `python3` is too old):

```bash
brew install python@3.12
python3.12 -m venv .venv
.venv/bin/pip install -e .
```

Start the bot: `.venv/bin/python -m src.main`. It binds to `127.0.0.1:8443` (only reachable via the local tunnel) and registers the webhook with Telegram on startup.

Don't run a polling instance with the same bot token anywhere else (e.g. on your laptop): polling mode calls `deleteWebhook` on startup and silently disconnects production. Use a separate BotFather bot for local development.

### 4. Verify

```bash
# Cloudflare terminates TLS and reaches the bot; expect 401 Unauthorized (no secret header).
# The route is POST-only, so a plain GET returns 405.
curl -i -X POST https://bot.your-domain.com/webhook

# Telegram's view — url should match, last_error_message should be absent
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"
```

If `getWebhookInfo` reports `403 Forbidden`, Cloudflare is likely challenging Telegram's requests: disable **Bot Fight Mode** (Security → Bots) for the zone.

### 5. Auto-start (macOS)

Install cloudflared as a launch agent for your user (it reads `~/.cloudflared/config.yml`):

```bash
cloudflared service install
```

Launch agents start when your user logs in, not at boot. On a headless Mac mini, enable **System Settings → Users & Groups → Automatically log in as** (requires FileVault to be off) so both the tunnel and the bot come back after a reboot or power loss.

Create `~/Library/LaunchAgents/app.voxara.bot.plist` for the bot itself (adjust paths):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>app.voxara.bot</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/YOU/voxara-bot/.venv/bin/python</string>
    <string>-m</string>
    <string>src.main</string>
  </array>
  <key>WorkingDirectory</key><string>/Users/YOU/voxara-bot</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>/Users/YOU/Library/Logs/voxara.out.log</string>
  <key>StandardErrorPath</key><string>/Users/YOU/Library/Logs/voxara.err.log</string>
</dict>
</plist>
```

Load: `launchctl load -w ~/Library/LaunchAgents/app.voxara.bot.plist`. The bot will restart on crash and start at login. The `.env` file is picked up from `WorkingDirectory`.

## Architecture

### Language registry

The bot is language-agnostic at its core. All language-specific behavior is defined in `src/tutor/languages.py` via the `LANGUAGES` dictionary. Each entry is a `LanguageConfig` that defines:

- **name**: Display name of the language
- **native_hints**: Common mistake patterns for specific native language speakers
- **example_corrections**: Few-shot examples for the system prompt
- **greeting**: Initial tutor greeting in the target language

### System prompt

The system prompt in `src/tutor/prompts.py` is fully parameterized — it references the target language name, native language hints, and user proficiency from the config, never hardcoding any language.

### Database

SQLite via aiosqlite. Key tables:
- `users` — includes `target_language` column
- `conversations` — snapshots `target_language` at conversation start
- `messages` — conversation history
- `error_log` — tracked corrections for analytics

### Adding a new language

Add an entry to the `LANGUAGES` dict in `src/tutor/languages.py`:

```python
"es": LanguageConfig(
    code="es",
    name="Spanish",
    native_hints={
        "ru": "Common issues for Russian speakers: subjunctive mood, ser vs estar...",
        "en": "Common issues for English speakers: ser vs estar, false cognates...",
    },
    example_corrections="...",
    greeting="¡Hola! Soy tu tutor de español. Hablemos...",
),
```

No other changes needed — the bot, prompts, DB, and handlers all work with any language in the registry.

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Set up your profile (name, target language, native language, level) |
| `/language` | Switch target language |
| `/level` | Change proficiency level (A1-C2) |
| `/reset` | End current conversation and start fresh |
| `/help` | Show available commands |

## Environment variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token (required) | — |
| `ANTHROPIC_API_KEY` | Anthropic API key (required) | — |
| `BOT_MODE` | `polling` or `webhook` | `polling` |
| `TELEGRAM_WEBHOOK_URL` | Webhook URL (required for webhook mode) | — |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook secret | — |
| `DATABASE_PATH` | SQLite database path | `./data/tutor.db` |
| `DEFAULT_TARGET_LANGUAGE` | Default target language code | `en` |
| `DEFAULT_PROFICIENCY` | Default proficiency level | `B2` |
| `DEFAULT_NATIVE_LANGUAGE` | Default native language code | `ru` |
| `MAX_CONTEXT_MESSAGES` | Max messages in context window | `20` |
| `MAX_CONTEXT_TOKENS` | Max estimated tokens for context | `6000` |
