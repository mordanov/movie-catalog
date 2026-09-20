from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    openai_api_key: str = ""
    tmdb_api_key: str = ""

    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "minioadmin"
    minio_root_password: str = "minioadmin"
    minio_bucket: str = "posters"

    web_user_1_login: str = ""
    web_user_1_password_hash: str = ""
    web_user_2_login: str = ""
    web_user_2_password_hash: str = ""

    jwt_secret: str = "change-me"
    jwt_expire_hours: int = 72


@lru_cache
def get_settings() -> Settings:
    return Settings()
