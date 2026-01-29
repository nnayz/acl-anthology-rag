"""
Pydantic schemas for request/response validation and data models.

This module defines the data structures used throughout the application
for type safety and API documentation. Schemas include:
- Paper metadata representation
- Search query and response models
- Embedding data structures
"""

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class QueryType(str, Enum):
    """Type of query detected from user input."""

    NATURAL_LANGUAGE = "natural_language"
    PAPER_ID = "paper_id"


class SearchMode(str, Enum):
    """Mode for search execution."""

    SEMANTIC = "semantic"  # Vector search only
    FILTER_ONLY = "filter_only"  # Filters only, no vector search
    HYBRID = "hybrid"  # Filters + vector search (default)


class YearFilter(BaseModel):
    """Filter for year-based queries."""

    exact: Optional[int] = Field(None, description="Exact year to match")
    min_year: Optional[int] = Field(None, description="Minimum year (inclusive)")
    max_year: Optional[int] = Field(None, description="Maximum year (inclusive)")

    @model_validator(mode="after")
    def validate_year_range(self) -> "YearFilter":
        if self.min_year and self.max_year and self.min_year > self.max_year:
            raise ValueError("min_year must be less than or equal to max_year")
        return self


class SearchFilters(BaseModel):
    """
    Structured filters for search queries.
    """

    year: Optional[YearFilter] = Field(None, description="Year filter (exact or range)")
    bibkey: Optional[str] = Field(None, description="Exact bibkey match")
    title_keywords: Optional[List[str]] = Field(
        None, description="Keywords to match in title"
    )
    language: Optional[str] = Field(None, description="Language filter")
    authors: Optional[List[str]] = Field(
        None, description="Author names to search for"
    )
    has_awards: Optional[bool] = Field(
        None, description="Filter for papers with any award"
    )
    awards: Optional[List[str]] = Field(
        None, description="Specific award names to match"
    )

    def is_empty(self) -> bool:
        """Check if no filters are set."""
        return all(
            v is None
            for v in [
                self.year,
                self.bibkey,
                self.title_keywords,
                self.language,
                self.authors,
                self.has_awards,
                self.awards,
            ]
        )


class ParsedQuery(BaseModel):
    """
    Result of parsing a natural language query into filters.
    """

    filters: Optional[SearchFilters] = Field(
        None, description="Extracted structured filters"
    )
    semantic_query: Optional[str] = Field(
        None, description="Remaining semantic search query after filter extraction"
    )
    original_query: str = Field(..., description="The original query string")


class QueryRequest(BaseModel):
    """Request schema for the query classification endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User query string - either natural language or ACL paper ID",
    )


class QueryClassification(BaseModel):
    """
    Response schema for query classification.
    """

    query_type: QueryType = Field(..., description="Detected type of the query")
    original_query: str = Field(..., description="The original query string")
    paper_id: Optional[str] = Field(
        None, description="Normalized paper ID if query_type is PAPER_ID"
    )
    is_valid: bool = Field(
        True, description="Whether the query is valid for processing"
    )


class PaperMetadata(BaseModel):
    """
    Schema for paper metadata returned from vector store.
    """

    paper_id: str
    title: str
    abstract: Optional[str] = None
    year: Optional[str] = None
    authors: Optional[List[str]] = None
    pdf_url: Optional[str] = None

    class Config:
        extra = "allow"


class SearchRequest(BaseModel):
    """Request schema for semantic search endpoint."""

    query: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=1000,
        description="Search query string (required for semantic/hybrid modes)",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return",
    )
    filters: Optional[SearchFilters] = Field(
        None, description="Explicit structured filters to apply"
    )
    mode: SearchMode = Field(
        default=SearchMode.HYBRID,
        description="Search mode: semantic, filter_only, or hybrid",
    )
    parse_filters_from_query: bool = Field(
        default=True,
        description="Whether to parse filters from the query using LLM",
    )

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> "SearchRequest":
        if self.mode in (SearchMode.SEMANTIC, SearchMode.HYBRID) and not self.query:
            raise ValueError(
                f"query is required for {self.mode.value} mode"
            )
        if self.mode == SearchMode.FILTER_ONLY and (
            not self.filters or self.filters.is_empty()
        ):
            raise ValueError("filters are required for filter_only mode")
        return self


class SearchResult(BaseModel):
    """
    Single search result with score and metadata.
    """

    paper: PaperMetadata
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class SearchResponse(BaseModel):
    """Response schema for search endpoint."""

    query_type: QueryType
    original_query: str
    results: List[SearchResult]
    paper_id: Optional[str] = Field(
        None, description="If query was a paper ID, the normalized ID"
    )
    source_paper: Optional[PaperMetadata] = Field(
        None,
        description="The paper referenced in the query (for paper ID queries)",
    )
    response: Optional[str] = Field(
        None,
        description="LLM-generated natural language response summarizing results (markdown format)",
    )
    mode: Optional[SearchMode] = Field(
        None, description="The search mode that was used"
    )
    parsed_filters: Optional[SearchFilters] = Field(
        None, description="Filters parsed from the natural language query"
    )
    applied_filters: Optional[SearchFilters] = Field(
        None, description="Filters that were actually applied to the search"
    )


class StreamEventType(str, Enum):
    """
    Types of events in streaming response.
    """

    METADATA = "metadata"  # Initial metadata (results, filters, etc.)
    CHUNK = "chunk"  # Text chunk from LLM response
    DONE = "done"  # Stream complete


class StreamEvent(BaseModel):
    """
    Single event in streaming response.
    """

    event: StreamEventType
    data: Optional[str] = None  # For CHUNK events


class StreamMetadata(BaseModel):
    """Metadata sent at start of streaming response."""

    query_type: QueryType
    original_query: str
    results: List[SearchResult]
    paper_id: Optional[str] = None
    source_paper: Optional[PaperMetadata] = None
    mode: Optional[SearchMode] = None
    parsed_filters: Optional[SearchFilters] = None
    applied_filters: Optional[SearchFilters] = None
    # Monitoring data
    semantic_query: Optional[str] = None
    reformulated_queries: Optional[List[str]] = None
    timestamps: Optional[Dict[str, float]] = None
