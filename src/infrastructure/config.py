from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Bilim"
    VERSION: str = "1.0.0"
    CORS_ORIGINS: list[str] = ["*"]

    # Database
    DATABASE_URL: str

    # Auth / JWT
    JWT_SECRET_KEY: str = "secrett"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"


# Instantiate once to be imported anywhere
settings = Settings()
