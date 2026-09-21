from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    openai_api_key: str = ""
    tmdb_api_key: str = ""

    s3_endpoint: str = "http://minio:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "posters"
    s3_key_prefix: str = ""  # e.g. "movie_posters/" to store in a subfolder
    s3_force_path_style: bool = True
    # Public base URL for stored objects. Empty = use relative /posters/<key> path
    # (proxied by nginx to MinIO in local dev). Set to full folder URL in production,
    # e.g. https://fsn1.your-objectstorage.com/mordanov-archive/movie_posters
    s3_public_url: str = ""

    web_user_1_login: str = ""
    web_user_1_password: str = ""
    web_user_2_login: str = ""
    web_user_2_password: str = ""

    jwt_secret: str = "change-me"
    jwt_expire_hours: int = 72

    bot_secret: str = ""  # shared secret for bot→backend calls; set in .env
    cookie_secure: bool = True  # set False for local HTTP dev


@lru_cache
def get_settings() -> Settings:
    return Settings()
