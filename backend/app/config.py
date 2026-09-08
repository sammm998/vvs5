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
    # a wall-clock budget for one analysis; without it a single dense page holds the worker forever
    analysis_deadline_s: int = 1800
    run_review: bool = True       # review agents check the finished result
    review_ocr: bool = True       # let the review read the page with OCR as an independent second opinion
    ocr_assist: bool = True       # let OCR name the characters the stroke recogniser could not
    # Ask a second reader about cases the geometry itself declared open, among the candidates the drawing offers.
    # Off by default: it costs a call and a wait per open case, and the reading is complete without it. Turning it
    # on also turns the determinism check off, because a reading that consulted another machine is not the same
    # kind of answer as one that did not - which the result then says outright.
    second_reader: bool = False
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    allow_registration: bool = True
    static_dir: str = ""          # built frontend (frontend/dist); served by the API when present

    @property
    def static_root(self) -> str:
        if self.static_dir:
            return self.static_dir
        return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

    model_config = {"env_prefix": "VVS_", "env_file": ".env", "extra": "ignore"}


settings = Settings()
os.makedirs(settings.storage_root, exist_ok=True)
if settings.database_url.startswith("sqlite:///"):
    os.makedirs(os.path.dirname(os.path.abspath(settings.database_url.replace("sqlite:///", ""))) or ".", exist_ok=True)
