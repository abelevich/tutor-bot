# Voxara Bot

A multilingual language tutor Telegram bot powered by any LLM (Claude by default, via [LiteLLM](https://docs.litellm.ai/)). Currently supports English, with an architecture designed to easily add more languages.

## How it works

Send the bot a message in the language you're learning. It will:
1. Reply naturally, continuing the conversation like a patient friend
2. Correct any mistakes with explanations, categorized by severity (critical / grammar / style)
3. Relate corrections to common patterns for your native language

## Setup

### 1. Create a Telegram bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram and create a new bot. Save the token.

### 2. Pick a model and get an API key

The bot talks to models through [LiteLLM](https://docs.litellm.ai/docs/providers), so any supported provider works. Set `LLM_MODEL` to `<provider>/<model>` and set that provider's API key:

| Provider | `LLM_MODEL` example | Key variable |
|----------|---------------------|--------------|
| Anthropic (default) | `anthropic/claude-sonnet-5-5` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai/gpt-5` | `OPENAI_API_KEY` |
| Google Gemini | `gemini/gemini-2.5-pro` | `GEMINI_API_KEY` |
| OpenRouter | `openrouter/<model>` | `OPENROUTER_API_KEY` |
| Ollama (local) | `ollama/llama3` | — (set `LLM_API_BASE=http://localhost:11434`) |

The tutor relies on the model following the `<reply>` / `<correction>` output format from the system prompt. Strong models do this reliably; with small or local models, check that corrections still show up.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your tokens:
#   TELEGRAM_BOT_TOKEN=your-bot-token
#   LLM_MODEL=anthropic/claude-sonnet-5-5
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
| `LLM_MODEL` | LiteLLM model string, `<provider>/<model>` | `anthropic/claude-sonnet-5-5` |
| `LLM_MAX_TOKENS` | Max tokens per tutor reply | `1024` |
| `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, ... | API key for the provider in `LLM_MODEL` (required, except for local models) | — |
| `LLM_API_KEY` | Optional explicit API key override | — |
| `LLM_API_BASE` | Optional custom endpoint (Ollama, vLLM, proxies) | — |
| `BOT_MODE` | `polling` or `webhook` | `polling` |
| `TELEGRAM_WEBHOOK_URL` | Webhook URL (required for webhook mode) | — |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook secret | — |
| `DATABASE_PATH` | SQLite database path | `./data/tutor.db` |
| `DEFAULT_TARGET_LANGUAGE` | Default target language code | `en` |
| `DEFAULT_PROFICIENCY` | Default proficiency level | `B2` |
| `DEFAULT_NATIVE_LANGUAGE` | Default native language code | `ru` |
| `MAX_CONTEXT_MESSAGES` | Max messages in context window | `20` |
| `MAX_CONTEXT_TOKENS` | Max estimated tokens for context | `6000` |
