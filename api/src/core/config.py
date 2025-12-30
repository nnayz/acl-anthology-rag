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

from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass
class Config:
    """
    Central configuration for the ACL Anthology RAG system.

    All configuration values are loaded from environment variables.
    This class serves as the single source of truth for application settings.

    Attributes:
        GROQ_API_KEY: API key for Groq LLM service.
    """

    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
