"""Application configuration via pydantic-settings."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://eidp:eidp@127.0.0.1:5432/eidp"
    log_level: str = "INFO"
    data_dir: Path = Path("./data")

    model_config = {"env_prefix": "EIDP_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
