"""
Configuration settings for the application.
Load from environment variables.
"""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "sqlite:///./papers.db"
    
    # Qdrant settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
    # LLM settings
    LLM_MODEL: str = "llama3"
    
    # Embedding model
    EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    
    class Config:
        env_file = ".env"

settings = Settings()