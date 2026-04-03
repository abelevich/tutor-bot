from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Telegram
    telegram_bot_token: str
    telegram_webhook_url: str = ""
    telegram_webhook_secret: str = ""

    # Anthropic
    anthropic_api_key: str

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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()  # type: ignore[call-arg]
