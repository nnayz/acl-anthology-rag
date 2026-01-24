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
    # ===================
    # API Keys & Endpoints
    # ===================
    FIREWORKS_API_KEY = os.getenv("FIREWORKS_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
    QDRANT_ENDPOINT = os.getenv("QDRANT_ENDPOINT")

    # ===================
    # LLM Settings
    # ===================
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "512"))

    # ===================
    # Embedding Settings
    # ===================
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")
    EMBEDDING_DIM = int(os.getenv("EMBEDDING_DIM", "768"))

    # ===================
    # Vector Database Settings
    # ===================
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "acl-anthology")
    QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "60"))

    # ===================
    # Retrieval Pipeline Settings
    # ===================
    NUM_REFORMULATED_QUERIES = int(os.getenv("NUM_REFORMULATED_QUERIES", "3"))
    SEARCH_K_MULTIPLIER = int(os.getenv("SEARCH_K_MULTIPLIER", "2"))

    # ===================
    # Result Aggregation Settings (RRF)
    # ===================
    RRF_K = int(
        os.getenv("RRF_K", "60")
    )  # RRF constant (higher = more weight to lower ranks)
    RRF_SCORE_WEIGHT = float(
        os.getenv("RRF_SCORE_WEIGHT", "0.3")
    )  # Weight for score vs rank fusion

    # ===================
    # Ingestion Settings
    # ===================
    EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "4"))


# Create a global settings object
settings = Settings()
