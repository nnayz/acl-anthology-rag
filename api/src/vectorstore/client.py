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

def get_qdrant_client(timeout: float = 60.0) -> QdrantClient:
    """
    Returns a Qdrant client using environment credentials.
    
    Args:
        timeout: Request timeout in seconds (default: 60s for large batch uploads)
    """
    return QdrantClient(
        url=settings.QDRANT_ENDPOINT,
        api_key=settings.QDRANT_API_KEY,
        timeout=timeout,  # Increased timeout for large batch operations
    )