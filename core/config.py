from dotenv import load_dotenv
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    ACCOUNTS_API_URL: str = os.getenv("ACCOUNTS_API_URL")
    CORS_ALLOWED_ORIGINS: list[str] = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,https://datapilotplatform.com,https://www.datapilotplatform.com,http://datapilotplatform.com,http://www.datapilotplatform.com,https://datapilotplataform.com,https://www.datapilotplataform.com,http://datapilotplataform.com,http://www.datapilotplataform.com",
        ).split(",")
        if origin.strip()
    ]

    ENV: str = os.getenv("ENV", "dev")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    TIMEOUT: int = int(os.getenv("TIMEOUT", 10))

    MAX_HISTORY_MESSAGES: int = int(os.getenv("MAX_HISTORY_MESSAGES", 10))
    MAX_ROWS: int = int(os.getenv("MAX_ROWS", 1000))


settings = Settings()
