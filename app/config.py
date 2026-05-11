from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "sqlite+aiosqlite:///./flight_scraper.db"

    # Scraper settings
    headless: bool = True
    scraper_timeout_seconds: int = 60
    scraper_max_retries: int = 2

    # Cache settings
    cache_ttl_minutes: int = 30

    # Debug settings
    debug_screenshots_dir: str = "./debug_screenshots"

    # Logging
    log_level: str = "INFO"

    # Respect robots.txt (disabled by default for scraping)
    respect_robots_txt: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
