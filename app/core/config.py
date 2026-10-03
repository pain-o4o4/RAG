from pydantic_settings import BaseSettings, SettingsConfigDict
import os
class Settings(BaseSettings):
    PROJECT_NAME: str = "RAG Backend API"
    API_V1: str = "/api/v1"
    API_V1_STR: str = "/api/v1"
    STORAGE_DIR: str = "./storage"
    UPLOAD_DIR: str = "./storage/uploads"
    VECTOR_STORE_DIR: str = "./storage/vector_store"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 4
    SIMILARITY_THRESHOLD: float = 0.45

    DATABASE_URL: str
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-004"
    LLM_MODEL: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env", 
        extra='ignore', 
        case_sensitive=False
    )

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_STORE_DIR, exist_ok=True)