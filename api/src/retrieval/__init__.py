"""
Retrieval module for semantic search over ACL Anthology papers.

This module handles the query-time retrieval workflow:
- Query interpretation (natural language vs paper ID)
- Fetching paper abstracts for paper-ID queries
- Result aggregation and ranking from multiple query embeddings

The retrieval pipeline provides a unified interface for both
query modalities described in the system design.
"""
