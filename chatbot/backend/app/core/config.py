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
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_SESSION_TOKEN: str = ""

    # Auth
    SECRET_KEY: str = "insecure-dev-key-replace-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_DAYS: int = 30

    # Database (chat history)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/chatbot.db"

    # CORS
    CORS_ORIGIN: str = "http://localhost:4200"

    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 25

    # App
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Redis — session DataFrame store + clarification state
    REDIS_URL: str = "redis://localhost:6379/0"

    # Snowflake connector
    SNOWFLAKE_ACCOUNT: str = ""
    SNOWFLAKE_USER: str = ""
    SNOWFLAKE_PASSWORD: str = ""
    SNOWFLAKE_WAREHOUSE: str = ""
    SNOWFLAKE_DATABASE: str = ""
    SNOWFLAKE_SCHEMA: str = "PUBLIC"
    SNOWFLAKE_ROLE: str = ""

    # BigQuery connector — ADC (Application Default Credentials)
    # Set GOOGLE_APPLICATION_CREDENTIALS to path of service account JSON file
    # OR mount ~/.config/gcloud into the container for gcloud auth
    BIGQUERY_PROJECT_ID: str = ""
    GOOGLE_APPLICATION_CREDENTIALS: str = ""

    # MSSQL connector (pyodbc)
    MSSQL_SERVER: str = ""
    MSSQL_DATABASE: str = ""
    MSSQL_USERNAME: str = ""
    MSSQL_PASSWORD: str = ""
    MSSQL_DRIVER: str = "ODBC Driver 18 for SQL Server"

    # Agent configuration
    INTENT_DIR: str = str(_BACKEND_DIR / "config" / "intents")
    PROMPT_DIR: str = str(_BACKEND_DIR / "config" / "prompts")
    MAX_DATAFRAME_ROWS: int = 10000
    MAX_TOOL_CALLS: int = 10
    DATAFRAME_TTL_SECONDS: int = 3600
    CLARIFICATION_TTL_SECONDS: int = 300


settings = Settings()
