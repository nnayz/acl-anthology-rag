"""
API route definitions.

This module defines the HTTP endpoints for the retrieval system:
- POST /search - Execute a semantic search query
- GET /paper/{acl_id} - Fetch paper metadata by ACL ID
"""

import logging

from fastapi import APIRouter, HTTPException, status

from src.core.schemas import (
    PaperMetadata,
    QueryClassification,
    QueryRequest,
    QueryType,
    SearchRequest,
    SearchResponse,
)
from src.retrieval.pipeline import get_pipeline
from src.retrieval.query_processor import detect_query_type, is_valid_acl_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/classify", response_model=QueryClassification)
async def classify_query(request: QueryRequest) -> QueryClassification:
    """
    Classify a user query to determine its type.

    Returns whether the query is a natural language search or an ACL paper ID.
    """
    query_type, paper_id = detect_query_type(request.query)

    return QueryClassification(
        query_type=QueryType(query_type.value),
        original_query=request.query,
        paper_id=paper_id,
        is_valid=True,
    )


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    Execute a semantic search query.

    For natural language queries: performs vector similarity search.
    For paper ID queries: looks up the paper and returns similar papers.
    """
    pipeline = get_pipeline()

    try:
        return await pipeline.search(request)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        # Return graceful empty response on error
        query_type, paper_id = detect_query_type(request.query)
        return SearchResponse(
            query_type=QueryType(query_type.value),
            original_query=request.query,
            paper_id=paper_id,
            results=[],
        )


@router.get("/paper/{paper_id}", response_model=PaperMetadata)
async def get_paper(paper_id: str) -> PaperMetadata:
    """
    Fetch paper metadata by ACL paper ID.

    Args:
        paper_id: ACL paper identifier (modern or legacy format)

    Returns:
        Paper metadata if found

    Raises:
        HTTPException 400: If paper_id format is invalid
        HTTPException 404: If paper not found
    """
    if not is_valid_acl_id(paper_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ACL paper ID format: {paper_id}",
        )

    pipeline = get_pipeline()
    paper = await pipeline._get_paper_by_id(paper_id)

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper not found: {paper_id}",
        )

    return paper
