"""
Application configuration management.

This module centralizes all configuration settings for the application,
loading values from environment variables with sensible defaults.

Configuration categories:
- LLM settings (API keys, model names)
- Vector database connection settings
- Embedding model configuration
- Retrieval parameters
"""

# from dataclasses import dataclass
# from dotenv import load_dotenv
# import os

# load_dotenv()


# @dataclass
# class Config:
#     """
#     Central configuration for the ACL Anthology RAG system.

#     All configuration values are loaded from environment variables.
#     This class serves as the single source of truth for application settings.

#     Attributes:
#         GROQ_API_KEY: API key for Groq LLM service.
#         QDRANT_API_KEY: API key for Qdrant vector database.
#         QDRANT_CLUSTER_ENDPOINT: Endpoint for Qdrant vector database.
#     """

#     GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
#     QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY")
#     QDRANT_ENDPOINT: str = os.getenv("QDRANT_ENDPOINT")
# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     GROQ_API_KEY: str
#     QDRANT_API_KEY: str
#     QDRANT_ENDPOINT: str
#     EMBEDDING_MODEL: str = "nomic-ai/nomic-embed-text-v1.5"

#     class Config:
#         env_file = ".env"

# settings = Settings()

import os
from dotenv import load_dotenv

# Load .env file automatically
load_dotenv()

class Settings:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_ENDPOINT = os.getenv("QDRANT_ENDPOINT")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")

# Create a global settings object
settings = Settings()
