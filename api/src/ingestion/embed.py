"""
Embedding generation for ACL Anthology abstracts.

This module handles the conversion of preprocessed text into
dense vector embeddings using a sentence transformer model.

The same embedding model must be used for both ingestion and
query-time embedding to ensure vector space consistency.
"""
