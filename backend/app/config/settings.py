# backend/app/config/settings.py
from __future__ import annotations
from pathlib import Path
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict
import os, tempfile

# Resolve repo root no matter where uvicorn is launched from
REPO_ROOT = Path(__file__).resolve().parents[3]

def _try_writable(p: Path) -> Path | None:
    try:
        p.mkdir(parents=True, exist_ok=True)
        t = p / ".write_test"
        t.write_text("ok", encoding="utf-8")
        t.unlink(missing_ok=True)
        return p.resolve()
    except Exception:
        return None

def _default_data_dir() -> Path:
    """
    HF Spaces:
      - /data is writable & persisted across restarts
      - /app is read-only (repo checkout)
    Order:
      1) DATA_DIR env (if set)
      2) /data
      3) <repo>/data
      4) temp dir
    """
    candidates: list[Path] = []
    env = os.getenv("DATA_DIR")
    if env:
        candidates.append(Path(env))
    candidates.append(Path("/data"))
    candidates.append(REPO_ROOT / "data")
    candidates.append(Path(tempfile.gettempdir()) / "pulsemaps" / "data")

    for p in candidates:
        w = _try_writable(p)
        if w:
            return w
    raise RuntimeError(f"No writable DATA_DIR found. Tried: {candidates!r}")

def _default_uploads_dir() -> Path:
    return (_default_data_dir() / "uploads").resolve()

def _default_frontend_dist() -> Path:
    return (REPO_ROOT / "web" / "dist").resolve()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # Models / API keys
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_AGENT: str = "gpt-4o"
    OPENAI_MODEL_CLASSIFIER: str = "gpt-4o-mini"

    # ✅ Google Maps (read from multiple env names for safety)
    google_maps_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VITE_GOOGLE_MAPS_API_KEY", "GOOGLE_MAPS_API_KEY"),
    )
    google_maps_map_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("VITE_GOOGLE_MAPS_MAP_ID", "VITE_GOOGLE_MAPS_MAP_IDY", "GOOGLE_MAPS_MAP_ID"),
    )

    # Paths
    DATA_DIR: Path = Field(default_factory=_default_data_dir)
    REPORTS_DB: Path | None = None
    SESSIONS_DB: Path | None = None
    UPLOADS_DIR: Path | None = None
    FRONTEND_DIST: Path = Field(default_factory=_default_frontend_dist)

    # Defaults
    DEFAULT_RADIUS_KM: float = 40.0
    DEFAULT_LIMIT: int = 10
    MAX_AGE_HOURS: int = 48

    # Optional extras
    firms_map_key: str | None = None
    gdacs_rss_url: str | None = "https://www.gdacs.org/xml/rss.xml"
    nvidia_api_key: str | None = None

    def ensure_dirs(self) -> None:
        # Fill derived paths if not explicitly provided
        if self.REPORTS_DB is None:
            self.REPORTS_DB = self.DATA_DIR / "pulsemaps_reports.db"
        if self.SESSIONS_DB is None:
            self.SESSIONS_DB = self.DATA_DIR / "pulsemap_sessions.db"
        if self.UPLOADS_DIR is None:
            self.UPLOADS_DIR = self.DATA_DIR / "uploads"

        # Create & resolve
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

        self.DATA_DIR = self.DATA_DIR.resolve()
        self.REPORTS_DB = self.REPORTS_DB.resolve()
        self.SESSIONS_DB = self.SESSIONS_DB.resolve()
        self.UPLOADS_DIR = self.UPLOADS_DIR.resolve()

settings = Settings()
settings.ensure_dirs()