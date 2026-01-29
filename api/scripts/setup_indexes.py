"""
Setup Qdrant payload indexes for efficient filtering.

This script creates payload indexes on the Qdrant collection
to enable efficient filtering by year, bibkey, language, etc.

Run this once after collection creation or when adding new filter capabilities.

Usage:
    cd api && python -m scripts.setup_indexes
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PayloadSchemaType,
    TextIndexParams,
    TextIndexType,
    TokenizerType,
)

from src.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_indexes(client: QdrantClient, collection_name: str, force: bool = False) -> None:
    """
    Create payload indexes for efficient filtering.

    Args:
        client: Qdrant client instance
        collection_name: Name of the collection to index
        force: If True, delete and recreate existing indexes
    """
    logger.info(f"Setting up indexes for collection: {collection_name}")

    # Keyword indexes for exact matching
    # Note: 'year' is stored as string in the payload, so it needs a KEYWORD index
    keyword_fields = ["bibkey", "language", "paper_id", "year"]
    for field in keyword_fields:
        try:
            if force:
                # Delete existing index first
                try:
                    client.delete_payload_index(
                        collection_name=collection_name,
                        field_name=field,
                    )
                    logger.info(f"Deleted existing index for '{field}'")
                except Exception:
                    pass  # Index might not exist

            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.info(f"Created keyword index for '{field}'")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Index for '{field}' already exists")
            else:
                logger.error(f"Failed to create index for '{field}': {e}")

    # Text indexes for partial matching (title, authors)
    text_fields = ["title", "authors"]
    text_index_params = TextIndexParams(
        type=TextIndexType.TEXT,
        tokenizer=TokenizerType.WORD,
        min_token_len=2,
        max_token_len=20,
        lowercase=True,
    )

    for field in text_fields:
        try:
            client.create_payload_index(
                collection_name=collection_name,
                field_name=field,
                field_schema=text_index_params,
            )
            logger.info(f"Created text index for '{field}'")
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info(f"Index for '{field}' already exists")
            else:
                logger.error(f"Failed to create index for '{field}': {e}")

    # Awards index (keyword for exact matching)
    try:
        client.create_payload_index(
            collection_name=collection_name,
            field_name="awards",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        logger.info("Created keyword index for 'awards'")
    except Exception as e:
        if "already exists" in str(e).lower():
            logger.info("Index for 'awards' already exists")
        else:
            logger.error(f"Failed to create index for 'awards': {e}")

    logger.info("Index setup complete")


def main():
    """Main entry point for index setup."""
    import argparse

    parser = argparse.ArgumentParser(description="Setup Qdrant payload indexes")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force recreate indexes (delete existing first)",
    )
    args = parser.parse_args()

    logger.info("Connecting to Qdrant...")

    client = QdrantClient(
        url=settings.QDRANT_ENDPOINT,
        api_key=settings.QDRANT_API_KEY,
        timeout=settings.QDRANT_TIMEOUT,
    )

    # Verify collection exists
    collection_name = settings.QDRANT_COLLECTION
    try:
        collection_info = client.get_collection(collection_name)
        logger.info(
            f"Collection '{collection_name}' found with "
            f"{collection_info.points_count} points"
        )
    except Exception as e:
        logger.error(f"Collection '{collection_name}' not found: {e}")
        sys.exit(1)

    # Setup indexes
    setup_indexes(client, collection_name, force=args.force)


if __name__ == "__main__":
    main()
