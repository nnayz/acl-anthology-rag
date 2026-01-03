"""
Vector database client.

This module provides the interface to the Qdrant vector database
for storing and querying paper embeddings. It handles connection
management, collection operations, and similarity search.
"""

# from src.core.config import settings
# from qdrant_client import QdrantClient

# def get_qdrant_client() -> QdrantClient:
#     """
#     Returns a Qdrant client using environment credentials.
#     """
#     return QdrantClient(
#         url=settings.QDRANT_ENDPOINT,
#         api_key=settings.QDRANT_API_KEY,
#     )

from qdrant_client import QdrantClient
from src.core.config import settings

def get_qdrant_client() -> QdrantClient:
    """
    Returns a Qdrant client using environment credentials.
    """
    return QdrantClient(
        url=settings.QDRANT_ENDPOINT,
        api_key=settings.QDRANT_API_KEY,
    )