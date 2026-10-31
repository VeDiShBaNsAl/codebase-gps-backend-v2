from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import json

class Settings(BaseSettings):
    github_token: str | None = None
    data_dir: str = "./data"
    database_url: str = "./data/codebase_gps.db"
    cors_origins: list[str] = Field(default=["http://localhost:5173"])
    max_repo_size_mb: int = 500
    clone_timeout_seconds: int = 120
    max_files: int = 10000
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
