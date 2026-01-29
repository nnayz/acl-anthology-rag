"""
LLM-based filter extraction from natural language queries.

This module uses an LLM to parse natural language search queries
into structured filters and remaining semantic search intent.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langchain_groq import ChatGroq

from src.core.config import settings
from src.core.schemas import ParsedQuery, SearchFilters, YearFilter
from src.llm.prompts import get_filter_extraction_prompt

logger = logging.getLogger(__name__)


def _create_fallback_runnable(fallback_value: Any) -> RunnableLambda:
    """Create a runnable that returns a constant fallback value."""
    return RunnableLambda(lambda _: fallback_value)


class FilterParser:
    """
    Parses natural language queries into structured filters using an LLM.

    Takes a user query and extracts:
    - Structured filters (year, authors, etc.)
    - Remaining semantic search intent

    Uses LangChain's LCEL with fallback handling for robustness.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the filter parser.

        Args:
            model_name: Groq model to use (default: from settings)
            temperature: LLM temperature (default: 0.0 for deterministic output)
        """
        self._model_name = model_name or settings.GROQ_MODEL
        # Use low temperature for consistent filter extraction
        self._temperature = temperature if temperature is not None else 0.0

        # Initialize Groq LLM
        self.llm = ChatGroq(
            model=self._model_name,
            temperature=self._temperature,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        # JSON output parser
        self.parser = JsonOutputParser()

        # Build LCEL chain with fallback
        self._build_chain()

    def _build_chain(self):
        """
        Build the LCEL chain with fallback handling.
        """
        base_chain = get_filter_extraction_prompt() | self.llm | self.parser

        # Fallback returns None, indicating parsing failed
        self.extraction_chain: RunnableWithFallbacks = base_chain.with_fallbacks(
            [_create_fallback_runnable(None)],
            exceptions_to_handle=(Exception,),
        )

    def _parse_year_filter(self, year_data: Optional[Dict]) -> Optional[YearFilter]:
        """
        Parse year filter from LLM output.
        """
        if not year_data:
            return None

        exact = year_data.get("exact")
        min_year = year_data.get("min_year")
        max_year = year_data.get("max_year")

        # Validate and clean up year values
        if exact is not None:
            try:
                exact = int(exact)
            except (TypeError, ValueError):
                exact = None

        if min_year is not None:
            try:
                min_year = int(min_year)
            except (TypeError, ValueError):
                min_year = None

        if max_year is not None:
            try:
                max_year = int(max_year)
            except (TypeError, ValueError):
                max_year = None

        # Return None if no valid values
        if exact is None and min_year is None and max_year is None:
            return None

        return YearFilter(exact=exact, min_year=min_year, max_year=max_year)

    def _parse_filters(self, filters_data: Optional[Dict]) -> Optional[SearchFilters]:
        """
        Parse SearchFilters from LLM output.
        """
        if not filters_data:
            return None

        year = self._parse_year_filter(filters_data.get("year"))
        bibkey = filters_data.get("bibkey")
        title_keywords = filters_data.get("title_keywords")
        language = filters_data.get("language")
        authors = filters_data.get("authors")
        has_awards = filters_data.get("has_awards")
        awards = filters_data.get("awards")

        # Clean up list fields
        if title_keywords and not isinstance(title_keywords, list):
            title_keywords = [title_keywords]
        if authors and not isinstance(authors, list):
            authors = [authors]
        if awards and not isinstance(awards, list):
            awards = [awards]

        filters = SearchFilters(
            year=year,
            bibkey=bibkey,
            title_keywords=title_keywords if title_keywords else None,
            language=language,
            authors=authors if authors else None,
            has_awards=has_awards if has_awards is True else None,
            awards=awards if awards else None,
        )

        return filters if not filters.is_empty() else None

    async def parse(self, query: str) -> ParsedQuery:
        """
        Parse a natural language query into structured filters.

        Args:
            query: User's natural language search query

        Returns:
            ParsedQuery with extracted filters and remaining semantic query
        """
        current_year = datetime.now(timezone.utc).year

        result = await self.extraction_chain.ainvoke(
            {
                "query": query,
                "current_year": current_year,
            }
        )

        if result is None:
            logger.warning("Filter extraction failed, returning original query only")
            return ParsedQuery(
                filters=None,
                semantic_query=query,
                original_query=query,
            )

        # Check relevance first
        is_relevant = result.get("is_relevant", True)
        if not is_relevant:
            irrelevant_response = result.get("irrelevant_response") or (
                "I'm an academic paper search assistant for computational linguistics and NLP research. "
                "I can help you find papers, explore research topics, discover authors' work, and more. "
                "Please ask me about NLP, machine learning, or computational linguistics papers!"
            )
            return ParsedQuery(
                filters=None,
                semantic_query=None,
                original_query=query,
                is_relevant=False,
                irrelevant_response=irrelevant_response,
            )

        # Parse the LLM output
        filters = self._parse_filters(result.get("filters"))
        semantic_query = result.get("semantic_query")

        # If semantic_query is empty string or whitespace, set to None
        if semantic_query and not semantic_query.strip():
            semantic_query = None

        logger.debug(f"Parsed filters: {filters}, semantic_query: {semantic_query}")

        return ParsedQuery(
            filters=filters,
            semantic_query=semantic_query,
            original_query=query,
            is_relevant=True,
        )


# Module-level singleton
_filter_parser: Optional[FilterParser] = None


def get_filter_parser() -> FilterParser:
    """Get or create the singleton FilterParser instance."""
    global _filter_parser
    if _filter_parser is None:
        _filter_parser = FilterParser()
    return _filter_parser
