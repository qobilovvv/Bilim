from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bilim"
    VERSION: str = "1.0.0"
    CORS_ORIGINS: list[str] = ["*"]

    MEDIA_ROOT: str = "media"

    # Database
    DB_POOL_SIZE: int = Field(default=5, ge=1, le=100)
    DB_MAX_OVERFLOW: int = Field(default=5, ge=0, le=100)
    DATABASE_URL: str

    # Auth / JWT
    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Eskiz SMS settings
    ESKIZ_BASE_URL: str = "https://notify.eskiz.uz/api"
    ESKIZ_EMAIL: str = ""
    ESKIZ_PASSWORD: str = ""
    ESKIZ_FROM: str = "4546"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(set(value)) < 8 or value.lower().startswith(("change", "replace", "your_")):
            raise ValueError("JWT_SECRET_KEY must be a strong, independently generated secret")
        return value


# Instantiate once to be imported anywhere
settings = Settings()
