import os
from typing import List


class Settings:
    FPL_BASE_URL = os.getenv("FPL_BASE_URL", "https://fantasy.premierleague.com/api")
    CONCURRENCY_LIMIT = int(os.getenv("FPL_CONCURRENCY_LIMIT", "3"))
    CACHE_TTL_SECONDS = int(os.getenv("FPL_CACHE_TTL_SECONDS", "600"))
    CACHE_MAX_ENTRIES = int(os.getenv("FPL_CACHE_MAX_ENTRIES", "500"))
    ALLOWED_ORIGINS = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "").split(",") if origin.strip()]
    APP_TITLE = os.getenv("APP_TITLE", "FPL Wrapped")
    DEFAULT_LIVE_TIMEOUT = float(os.getenv("FPL_DEFAULT_LIVE_TIMEOUT", "10.0"))
    EXTENDED_POLL_SECONDS = int(os.getenv("EXTENDED_POLL_SECONDS", "2"))
