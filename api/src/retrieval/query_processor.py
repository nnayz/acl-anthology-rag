"""
Query processing and interpretation.

This module determines the type of user query (natural language or
paper ID) and routes it appropriately. For paper ID queries, it
fetches the corresponding abstract to use as a semantic proxy.

Supports both:
1. Direct paper ID queries (e.g., "2021.ccl-1.10")
2. Natural language queries containing paper IDs (e.g., "find similar papers to 2021.ccl-1.10")
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
MODERN_ID_PATTERN = re.compile(r"\d{4}\.[a-z0-9]+-[a-z0-9]+\.\d+", re.IGNORECASE)

# Legacy format: L-YY-NNNN (e.g., A00-1000, W99-0512)
LEGACY_ID_PATTERN = re.compile(r"[A-Z]\d{2}-\d{4}", re.IGNORECASE)


def is_valid_acl_id(query: str) -> bool:
    """
    Check if a query string matches a valid ACL paper ID format.

    Args:
        query: The input string to validate

    Returns:
        True if the query matches either modern or legacy ACL ID format
    """
    query = query.strip()
    return bool(
        re.fullmatch(MODERN_ID_PATTERN.pattern, query, re.IGNORECASE) or 
        re.fullmatch(LEGACY_ID_PATTERN.pattern, query, re.IGNORECASE)
    )


def normalize_paper_id(paper_id: str) -> str:
    """
    Normalize a paper ID to a consistent format.
    
    Args:
        paper_id: Raw paper ID string
        
    Returns:
        Normalized paper ID
    """
    paper_id = paper_id.strip()
    if re.fullmatch(LEGACY_ID_PATTERN.pattern, paper_id, re.IGNORECASE):
        # Legacy format: uppercase the letter
        return paper_id[0].upper() + paper_id[1:]
    else:
        # Modern format: keep as lowercase
        return paper_id.lower()


def extract_paper_id_regex(query: str) -> Optional[str]:
    """
    Try to extract a paper ID from query using regex.
    
    Args:
        query: User query string
        
    Returns:
        Extracted paper ID or None
    """
    # Try modern format first
    modern_match = MODERN_ID_PATTERN.search(query)
    if modern_match:
        return normalize_paper_id(modern_match.group())
    
    # Try legacy format
    legacy_match = LEGACY_ID_PATTERN.search(query)
    if legacy_match:
        return normalize_paper_id(legacy_match.group())
    
    return None


def detect_query_type(query: str) -> Tuple[QueryType, Optional[str]]:
    """
    Determine the type of user query using regex-based detection.

    Args:
        query: The raw user input string

    Returns:
        Tuple of (QueryType, normalized_id_or_none)
        - For paper ID queries: (PAPER_ID, normalized_paper_id)
        - For natural language: (NATURAL_LANGUAGE, None)
    """
    cleaned = query.strip()

    # Check if entire query is a paper ID
    if is_valid_acl_id(cleaned):
        return (QueryType.PAPER_ID, normalize_paper_id(cleaned))

    # Try to extract paper ID from within the query
    extracted_id = extract_paper_id_regex(cleaned)
    if extracted_id:
        return (QueryType.PAPER_ID, extracted_id)

    return (QueryType.NATURAL_LANGUAGE, None)
