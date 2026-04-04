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
