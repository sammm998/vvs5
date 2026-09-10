from __future__ import annotations

import os
from pydantic_settings import BaseSettings

DEV_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    app_name: str = "VVS Mängdning"
    database_url: str = "sqlite:///./data/vvs.db"
    storage_root: str = "./data/storage"
    # Nyckeln varje inloggningsbevis undertecknas med. Standardvärdet står i källkoden, och en tjänst som
    # startar med det undertecknar alltså varje bevis med en sträng vem som helst kan läsa - då går det att
    # skriva sitt eget bevis för vilket konto som helst, adminkontot inräknat. Se `demand_a_real_secret()`.
    secret_key: str = DEV_SECRET
    access_token_minutes: int = 60 * 24
    worker_threads: int = 1
    run_determinism: bool = False
    # a wall-clock budget for one analysis; without it a single dense page holds the worker forever
    analysis_deadline_s: int = 1800
    run_review: bool = True       # review agents check the finished result
    # De två OCR-passen är avstängda som standard, för de är mätta och de kostade mer än de gav.
    #
    # `review_ocr` är synagentens korsprov: den läser sidan en gång till och säger om den ser en beteckning där
    # vektorläsningen inte har någon text. Den kan aldrig ändra ett mått - granskningen får inte röra läsningen
    # - och den kostade 17 s av 75 s på blad A. Vad man förlorar är en varning, inte en meter.
    #
    # `ocr_assist` får namnge tecken som streckläsaren inte kunde. Mätt på tre blad kostade den 15-17 s och
    # ändrade ingenting: A0124 löste 0 av 59 okända tecken, B0122 0 av 30, A 3 av 24 - och mängden blev
    # identisk i alla tre fallen. På de tyngre bladen är den halva analystiden.
    #
    # Båda går att slå på igen: VVS_REVIEW_OCR=true / VVS_OCR_ASSIST=true, eller under Administration för den
    # här tjänsten. En installation vars ritningar är sämre lästa kan mycket väl vilja ha dem på.
    review_ocr: bool = False      # let the review read the page with OCR as an independent second opinion
    ocr_assist: bool = False      # let OCR name the characters the stroke recogniser could not
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


def demand_a_real_secret() -> None:
    """Vägra starta i drift med den nyckel som står i källkoden.

    Ett bevis undertecknat med en publik sträng är inget bevis. Vem som helst som läst koden kan skriva sitt
    eget för vilket konto som helst, och ingenting i tjänsten skulle märka det - inte inloggningen, inte
    ägarkontrollen, inte adminspärren.

    Att skrika vid start är hela poängen. Ett varningsmeddelande i en logg ingen läser är samma sak som
    ingenting; en tjänst som inte går upp märks inom en minut, och felet står i klartext med vad som ska
    sättas. På en utvecklingsmaskin är standardvärdet däremot precis vad man vill ha, så det som avgör är
    om något säger att det här är drift.
    """
    if settings.secret_key != DEV_SECRET:
        return
    dev = (os.environ.get("VVS_DEV") == "1"
           or os.environ.get("PYTEST_CURRENT_TEST")
           or not any(os.environ.get(k) for k in
                      ("RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID", "RAILWAY_SERVICE_ID",
                       "FLY_APP_NAME", "RENDER", "HEROKU_APP_NAME", "KUBERNETES_SERVICE_HOST",
                       "VVS_PRODUCTION")))
    if dev:
        return
    raise RuntimeError(
        "VVS_SECRET_KEY är inte satt. Tjänsten skulle underteckna varje inloggningsbevis med den nyckel som "
        "står i källkoden, och då kan vem som helst skriva sitt eget bevis för vilket konto som helst. "
        "Sätt VVS_SECRET_KEY till en lång slumpsträng - till exempel `python -c \"import secrets; "
        "print(secrets.token_urlsafe(48))\"` - och starta om.")


os.makedirs(settings.storage_root, exist_ok=True)
if settings.database_url.startswith("sqlite:///"):
    os.makedirs(os.path.dirname(os.path.abspath(settings.database_url.replace("sqlite:///", ""))) or ".", exist_ok=True)
