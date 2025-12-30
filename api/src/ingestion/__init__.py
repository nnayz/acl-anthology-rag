"""
Ingestion module for ACL Anthology data preparation.

This module handles the offline data preparation workflow:
1. Downloading abstracts and metadata from ACL Anthology
2. Preprocessing and cleaning text data
3. Generating dense vector embeddings
4. Storing embeddings in the vector database

The ingestion pipeline runs as a batch process before the system
is ready to serve queries.
"""
