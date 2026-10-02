from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Export .env into os.environ so LiteLLM can find provider API keys
# (ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY, ...).
load_dotenv()


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""

    # LLM (any LiteLLM model string: "<provider>/<model>")
    llm_model: str = "anthropic/claude-sonnet-5-5"
    llm_max_tokens: int = 1024
    # Optional overrides; by default LiteLLM reads the provider's own env var
    llm_api_key: str = ""
    llm_api_base: str = ""  # e.g. http://localhost:11434 for Ollama

    # Database
    database_path: str = "./data/tutor.db"

    # Bot mode
    bot_mode: str = "polling"  # "webhook" or "polling"

    # Tutor defaults
    default_target_language: str = "en"
    default_proficiency: str = "B2"
    default_native_language: str = "ru"
    max_context_messages: int = 20
    max_context_tokens: int = 6000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        # Provider keys (ANTHROPIC_API_KEY, ...) live in .env but are read by LiteLLM
        "extra": "ignore",
    }


settings = Settings()  # type: ignore[call-arg]
