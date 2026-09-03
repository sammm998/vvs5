from __future__ import annotations

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "VVS Mängdning"
    database_url: str = "sqlite:///./data/vvs.db"
    storage_root: str = "./data/storage"
    secret_key: str = "change-me-in-production"
    access_token_minutes: int = 60 * 24
    worker_threads: int = 1
    run_determinism: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    allow_registration: bool = True

    model_config = {"env_prefix": "VVS_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
os.makedirs(settings.storage_root, exist_ok=True)
if settings.database_url.startswith("sqlite:///"):
    os.makedirs(os.path.dirname(os.path.abspath(settings.database_url.replace("sqlite:///", ""))) or ".", exist_ok=True)
