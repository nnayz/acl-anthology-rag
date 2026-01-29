"""
Qdrant filter construction from structured search filters.

This module converts SearchFilters into Qdrant Filter objects
for efficient payload-based filtering in vector searches.
"""

import logging
from typing import List, Optional

from qdrant_client.models import (
    FieldCondition,
    Filter,
    IsEmptyCondition,
    MatchAny,
    MatchText,
    MatchValue,
    PayloadField,
    Range,
)

from src.core.schemas import SearchFilters, YearFilter

logger = logging.getLogger(__name__)


class QdrantFilterBuilder:
    """
    Builds Qdrant Filter objects from SearchFilters.

    Converts structured filter specifications into Qdrant's
    Filter model for use in query_points and scroll operations.

    Supported filters:
    - year: Exact match or range query on integer year field
    - bibkey: Exact match on bibkey field
    - title_keywords: Text match (partial) on title field
    - language: Exact match on language field
    - authors: Text match on authors field (searches within array)
    - has_awards: Existence check for awards field
    - awards: Match any of specified award names
    """

    def build(self, filters: SearchFilters) -> Optional[Filter]:
        """
        Build a Qdrant Filter from SearchFilters.

        Args:
            filters: Structured search filters

        Returns:
            Qdrant Filter object, or None if no filters are set
        """
        if filters.is_empty():
            return None

        # Qdrant Filter.must accepts a list of Condition objects
        must_conditions: List = []
        must_not_conditions: List = []

        # Year filter
        if filters.year:
            year_conditions = self._build_year_conditions(filters.year)
            must_conditions.extend(year_conditions)

        # Bibkey filter (exact match)
        if filters.bibkey:
            must_conditions.append(
                FieldCondition(
                    key="bibkey",
                    match=MatchValue(value=filters.bibkey),
                )
            )

        # Title keywords (text match)
        if filters.title_keywords:
            for keyword in filters.title_keywords:
                must_conditions.append(
                    FieldCondition(
                        key="title",
                        match=MatchText(text=keyword),
                    )
                )

        # Language filter (exact match)
        if filters.language:
            must_conditions.append(
                FieldCondition(
                    key="language",
                    match=MatchValue(value=filters.language),
                )
            )

        # Authors filter (text match for partial matching)
        if filters.authors:
            for author in filters.authors:
                must_conditions.append(
                    FieldCondition(
                        key="authors",
                        match=MatchText(text=author),
                    )
                )

        # Awards filters
        if filters.has_awards is True:
            # Check if awards field exists and is not empty
            # Use must_not with IsEmptyCondition to require non-empty
            must_not_conditions.append(
                IsEmptyCondition(
                    is_empty=PayloadField(key="awards"),
                )
            )
        elif filters.awards:
            # Match specific award names
            must_conditions.append(
                FieldCondition(
                    key="awards",
                    match=MatchAny(any=filters.awards),
                )
            )

        if not must_conditions and not must_not_conditions:
            return None

        return Filter(
            must=must_conditions if must_conditions else None,
            must_not=must_not_conditions if must_not_conditions else None,
        )

    def _build_year_conditions(self, year_filter: YearFilter) -> List[FieldCondition]:
        """
        Build year filter conditions.

        Note: Year is stored as a STRING in the payload (e.g., "2022"),
        so we use MatchAny with string values instead of Range queries.

        Args:
            year_filter: Year filter specification

        Returns:
            List of FieldCondition objects for year filtering
        """
        conditions = []

        if year_filter.exact is not None:
            # Exact year match - convert to string
            conditions.append(
                FieldCondition(
                    key="year",
                    match=MatchValue(value=str(year_filter.exact)),
                )
            )
        else:
            # Range query - generate list of year strings to match
            # Since year is stored as string, Range won't work
            min_year = year_filter.min_year or 1965  # ACL started ~1965
            max_year = year_filter.max_year or 2026  # Current year

            # Limit range to avoid huge lists (max 50 years)
            if max_year - min_year > 50:
                min_year = max_year - 50
                logger.warning(
                    f"Year range too large, limiting to {min_year}-{max_year}"
                )

            year_strings = [str(y) for y in range(min_year, max_year + 1)]

            if year_strings:
                conditions.append(
                    FieldCondition(
                        key="year",
                        match=MatchAny(any=year_strings),
                    )
                )

        return conditions


# Module-level singleton
_filter_builder: Optional[QdrantFilterBuilder] = None


def get_filter_builder() -> QdrantFilterBuilder:
    """Get or create the singleton QdrantFilterBuilder instance."""
    global _filter_builder
    if _filter_builder is None:
        _filter_builder = QdrantFilterBuilder()
    return _filter_builder
