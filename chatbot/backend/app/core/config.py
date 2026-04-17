from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env regardless of where uvicorn is invoked from.
# Priority (last wins): chatbot/backend/.env  →  chatbot/.env
_BACKEND_DIR = Path(__file__).parents[2]   # …/chatbot/backend
_CHATBOT_DIR = Path(__file__).parents[3]   # …/chatbot


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            str(_BACKEND_DIR / ".env"),   # standard: next to requirements.txt
            str(_CHATBOT_DIR / ".env"),   # monorepo root: chatbot/.env
        ],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM providers
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    LLM_PROVIDER: str = "anthropic"

    # AWS Bedrock — credentials fall back to boto3 credential chain
    # (env vars, ~/.aws/credentials, EC2/ECS instance role)
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_SESSION_TOKEN: str = ""

    # Auth
    SECRET_KEY: str = "insecure-dev-key-replace-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/chatbot.db"

    # CORS
    CORS_ORIGIN: str = "http://localhost:4200"

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 25

    # App
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False


settings = Settings()
