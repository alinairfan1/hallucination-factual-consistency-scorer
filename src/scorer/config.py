from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SCORER_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./scorer.db"
    judge_model: str = "claude-sonnet-5"
    anthropic_api_key: str = ""


settings = Settings()
