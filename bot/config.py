from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str
    initial_admin_telegram_id: int
    backend_url: str = "http://backend:8000"
    bot_secret: str = ""  # must match backend BOT_SECRET


settings = Settings()
