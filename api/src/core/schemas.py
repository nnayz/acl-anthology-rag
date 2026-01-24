"""
Pydantic schemas for request/response validation and data models.

This module defines the data structures used throughout the application
for type safety and API documentation. Schemas include:
- Paper metadata representation
- Search query and response models
- Embedding data structures
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Type of query detected from user input."""

    NATURAL_LANGUAGE = "natural_language"
    PAPER_ID = "paper_id"


class QueryRequest(BaseModel):
    """Request schema for the query classification endpoint."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="User query string - either natural language or ACL paper ID",
    )


class QueryClassification(BaseModel):
    """Response schema for query classification."""

    query_type: QueryType = Field(..., description="Detected type of the query")
    original_query: str = Field(..., description="The original query string")
    paper_id: Optional[str] = Field(
        None, description="Normalized paper ID if query_type is PAPER_ID"
    )
    is_valid: bool = Field(
        True, description="Whether the query is valid for processing"
    )


class PaperMetadata(BaseModel):
    """Schema for paper metadata returned from vector store."""

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

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query string",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of results to return",
    )


class SearchResult(BaseModel):
    """Single search result with score and metadata."""

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
