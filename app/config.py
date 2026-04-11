from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).parent.parent


class Settings(BaseSettings):
    OPENAI_API_KEY: str = ""
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/app.db"
    APP_ENV: str = "development"
    MAX_ARTICLES_PER_TOPIC: int = 100
    COLLECTION_INTERVAL_MINUTES: int = 60
    SYNTHESIS_INTERVAL_HOURS: int = 24
    SYNTHESIS_MIN_NEW_ARTICLES: int = 3
    REQUEST_TIMEOUT_SECONDS: int = 20
    USER_AGENT: str = "NewsIntelDashboard/1.0"
    ENABLE_SCHEDULER: bool = False

    TOPICS_CONFIG: Path = BASE_DIR / "config" / "topics.json"
    SOURCES_CONFIG: Path = BASE_DIR / "config" / "sources.json"
    SYNTHESIS_SYSTEM_PROMPT: Path = BASE_DIR / "config" / "prompt_templates" / "synthesis_system.txt"
    SYNTHESIS_USER_PROMPT: Path = BASE_DIR / "config" / "prompt_templates" / "synthesis_user.txt"

    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_MAX_TOKENS: int = 2000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
