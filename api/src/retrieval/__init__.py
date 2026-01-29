"""
Retrieval module for semantic search over ACL Anthology papers.

This module handles the query-time retrieval workflow:
- Query interpretation (natural language vs paper ID)
- Filter extraction from natural language queries
- Qdrant filter construction for payload filtering
- Fetching paper abstracts for paper-ID queries
- Result aggregation and ranking from multiple query embeddings

The retrieval pipeline provides a unified interface for:
- Semantic search (vector similarity)
- Filter-only search (payload filtering)
- Hybrid search (filters + vector similarity)
"""

from src.retrieval.filter_builder import QdrantFilterBuilder, get_filter_builder
from src.retrieval.filter_parser import FilterParser, get_filter_parser
from src.retrieval.pipeline import RetrievalPipeline, get_pipeline

__all__ = [
    "RetrievalPipeline",
    "get_pipeline",
    "FilterParser",
    "get_filter_parser",
    "QdrantFilterBuilder",
    "get_filter_builder",
]
