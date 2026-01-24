"""
Vector database client and LangChain component management.

This module provides centralized singleton management for all LangChain
components used in the ACL Anthology RAG system:
- QdrantClient for vector database operations
- FireworksEmbeddings for text embedding (via Fireworks API)
- QdrantVectorStore for LangChain-integrated vector search

Using singletons ensures:
- Consistent embedding model across ingestion and retrieval
- Efficient resource usage (models loaded once)
- Thread-safe access to shared components
"""

from threading import Lock
from typing import Optional

from langchain_fireworks import FireworksEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.core.config import settings


class LangChainComponents:
    """
    Centralized singleton manager for LangChain components.

    Provides thread-safe lazy initialization of:
    - Qdrant client
    - Fireworks embeddings model (via API)
    - Qdrant vector store

    Usage:
        components = get_langchain_components()
        embeddings = components.embeddings
        vectorstore = components.vectorstore
    """

    _instance: Optional["LangChainComponents"] = None
    _lock: Lock = Lock()

    def __new__(cls) -> "LangChainComponents":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._qdrant_client: Optional[QdrantClient] = None
        self._embeddings: Optional[FireworksEmbeddings] = None
        self._vectorstore: Optional[QdrantVectorStore] = None
        self._timeout: int = settings.QDRANT_TIMEOUT
        self._initialized = True

    def configure(
        self,
        timeout: Optional[int] = None,
        **kwargs,
    ) -> "LangChainComponents":
        """
        Configure component settings before initialization.

        Args:
            timeout: Request timeout for Qdrant client (default: from settings)
            **kwargs: Additional arguments (ignored for API-based embeddings)

        Returns:
            Self for method chaining
        """
        if timeout is not None:
            self._timeout = timeout
        return self

    @property
    def qdrant_client(self) -> QdrantClient:
        """Lazy-load and return the Qdrant client singleton."""
        if self._qdrant_client is None:
            self._qdrant_client = QdrantClient(
                url=settings.QDRANT_ENDPOINT,
                api_key=settings.QDRANT_API_KEY,
                timeout=self._timeout,
            )
        return self._qdrant_client

    @property
    def embeddings(self) -> FireworksEmbeddings:
        """Lazy-load and return the embeddings model singleton."""
        if self._embeddings is None:
            self._embeddings = FireworksEmbeddings(
                model=settings.EMBEDDING_MODEL,
            )
        return self._embeddings

    @property
    def vectorstore(self) -> QdrantVectorStore:
        """Lazy-load and return the vector store singleton."""
        if self._vectorstore is None:
            self._vectorstore = QdrantVectorStore(
                client=self.qdrant_client,
                collection_name=settings.QDRANT_COLLECTION,
                embedding=self.embeddings,
            )
        return self._vectorstore

    def get_vectorstore(
        self,
        collection_name: Optional[str] = None,
    ) -> QdrantVectorStore:
        """
        Get a vector store for a specific collection.

        Args:
            collection_name: Collection name (default: from settings)

        Returns:
            QdrantVectorStore instance
        """
        if collection_name is None or collection_name == settings.QDRANT_COLLECTION:
            return self.vectorstore

        return QdrantVectorStore(
            client=self.qdrant_client,
            collection_name=collection_name,
            embedding=self.embeddings,
        )


# Global singleton instance
_components: Optional[LangChainComponents] = None


def get_langchain_components() -> LangChainComponents:
    """Get or create the singleton LangChainComponents instance."""
    global _components
    if _components is None:
        _components = LangChainComponents()
    return _components


# Convenience functions for backward compatibility
def get_qdrant_client(timeout: Optional[int] = None) -> QdrantClient:
    """
    Returns the Qdrant client singleton.

    Args:
        timeout: Request timeout in seconds (default: from settings)
    """
    return get_langchain_components().configure(timeout=timeout).qdrant_client


def get_embeddings(**kwargs) -> FireworksEmbeddings:
    """
    Returns the embeddings model singleton.

    Args:
        **kwargs: Ignored (kept for backward compatibility)
    """
    return get_langchain_components().embeddings


def get_vectorstore(
    collection_name: Optional[str] = None,
    **kwargs,
) -> QdrantVectorStore:
    """
    Returns a LangChain Qdrant vector store connected to the collection.

    Args:
        collection_name: Name of the Qdrant collection (default: from settings)
        **kwargs: Ignored (kept for backward compatibility)

    Returns:
        Configured QdrantVectorStore instance
    """
    return get_langchain_components().get_vectorstore(collection_name)
