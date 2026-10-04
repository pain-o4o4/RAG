import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
_ENV_FILE = _ROOT_DIR / ".env"

class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Backend API"
    API_V1: str = "/api/v1"
    API_V1_STR: str = "/api/v1"
    STORAGE_DIR: str = str(_ROOT_DIR / "storage")
    UPLOAD_DIR: str = str(_ROOT_DIR / "storage" / "uploads")
    VECTOR_STORE_DIR: str = str(_ROOT_DIR / "storage" / "vector_store")
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 4
    SIMILARITY_THRESHOLD: float = 0.20

    DATABASE_URL: str = ""
    GEMINI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "gemini-embedding-2"
    LLM_MODEL: str = "gemini-flash-latest"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        extra="ignore",
        case_sensitive=False
    )

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)
