"""
Query processing and interpretation.

This module determines the type of user query (natural language or
paper ID) and routes it appropriately. For paper ID queries, it
fetches the corresponding abstract to use as a semantic proxy.
"""

import re
from enum import Enum
from typing import Optional, Tuple


class QueryType(Enum):
    """Enumeration of supported query types."""

    NATURAL_LANGUAGE = "natural_language"
    PAPER_ID = "paper_id"


# Regex patterns for ACL paper ID formats
# Modern format: YYYY.venue-code.number (e.g., 2023.acl-long.412)
MODERN_ID_PATTERN = re.compile(r"^\d{4}\.[a-z0-9]+-[a-z0-9]+\.\d+$", re.IGNORECASE)

# Legacy format: L-YY-NNNN (e.g., A00-1000, W99-0512)
LEGACY_ID_PATTERN = re.compile(r"^[A-Z]\d{2}-\d{4}$", re.IGNORECASE)


def is_valid_acl_id(query: str) -> bool:
    """
    Check if a query string matches a valid ACL paper ID format.

    Args:
        query: The input string to validate

    Returns:
        True if the query matches either modern or legacy ACL ID format
    """
    query = query.strip()
    return bool(MODERN_ID_PATTERN.match(query) or LEGACY_ID_PATTERN.match(query))


def detect_query_type(query: str) -> Tuple[QueryType, Optional[str]]:
    """
    Determine the type of user query.

    Args:
        query: The raw user input string

    Returns:
        Tuple of (QueryType, normalized_id_or_none)
        - For paper ID queries: (PAPER_ID, normalized_paper_id)
        - For natural language: (NATURAL_LANGUAGE, None)
    """
    cleaned = query.strip()

    if is_valid_acl_id(cleaned):
        # Normalize paper ID
        if LEGACY_ID_PATTERN.match(cleaned):
            # Legacy format: uppercase the letter
            normalized = cleaned[0].upper() + cleaned[1:]
        else:
            # Modern format: keep as lowercase
            normalized = cleaned.lower()
        return (QueryType.PAPER_ID, normalized)

    return (QueryType.NATURAL_LANGUAGE, None)
