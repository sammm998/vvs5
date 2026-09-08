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
    #
    # Unset means: on where this installation holds an OPENAI_API_KEY, off where it does not. Putting that key
    # into a service that has exactly one use for it is the operator saying yes; making them also set a second
    # flag only produces the case where the key is there and nothing happens. `true` forces it on (a machine
    # behind a proxy that attaches the credential has no key of its own), `false` forces it off whatever else is
    # configured. Either way, a reading that consulted it says so, and reports no determinism state it cannot
    # honestly claim.
    second_reader: bool | None = None
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
