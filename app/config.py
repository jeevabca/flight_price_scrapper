from pydantic_settings import BaseSettings
from functools import lru_cache
import yaml
import os
import re
from dotenv import load_dotenv

def load_yaml_config(filepath: str = "config.yaml") -> dict:
    """Loads a YAML file and resolves ${VAR:default} style variables."""
    # Load .env variables into os.environ so they are accessible to the YAML parser
    load_dotenv()
    
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Regex to resolve ${VAR_NAME:default_value} or ${VAR_NAME}
    pattern = re.compile(r'\$\{([^}^{:]+)(?::([^}^{]*))?\}')
    
    def replacer(match):
        var_name = match.group(1)
        default_val = match.group(2) or ''
        return os.environ.get(var_name, default_val)
        
    resolved_content = pattern.sub(replacer, content)
    return yaml.safe_load(resolved_content) or {}

# Load yaml configuration once
_yaml_config = load_yaml_config("config.yaml")
_db_config = _yaml_config.get("postgres", {})

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    postgres_host: str = _db_config.get("host", "127.0.0.1")
    postgres_port: str = str(_db_config.get("port", "5432"))
    postgres_database: str = _db_config.get("database", "Dfdsfasdas")
    postgres_user: str = _db_config.get("user", "postgres")
    postgres_password: str = _db_config.get("password", "jee3444")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"

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

    # LLM settings
    groq_api_key: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
