from functools import lru_cache
import os

from dotenv import load_dotenv
from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str
    debug: bool

    redis_url: str

    gemini_api_key: str
    gemini_model: str

    session_cookie_name: str
    session_ttl_seconds: int

    ai_rate_limit_per_minute: int
    ai_rate_window_seconds: int

    cors_origins: str

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        app_name=os.getenv("APP_NAME", "ATS Resume Builder"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "rb_session"),
        session_ttl_seconds=int(os.getenv("SESSION_TTL_SECONDS", str(60 * 60 * 24 * 14))),
        ai_rate_limit_per_minute=int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "30")),
        ai_rate_window_seconds=int(os.getenv("AI_RATE_WINDOW_SECONDS", "60")),
        cors_origins=os.getenv("CORS_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000"),
    )
