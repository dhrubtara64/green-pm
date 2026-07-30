from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://greenpm:greenpm@db:5432/greenpm"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    cors_origins: list[str] = ["http://localhost:3000", "http://frontend:3000"]
    log_level: str = "INFO"

    class Config:
        env_file = ".env"


settings = Settings()
