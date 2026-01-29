"""
API route definitions.

This module defines the HTTP endpoints for the retrieval system:
- POST /search - Execute a semantic search query with streaming response (SSE)
- GET /paper/{acl_id} - Fetch paper metadata by ACL ID

Search modes:
- SEMANTIC: Vector search only
- FILTER_ONLY: Payload filtering without vector search
- HYBRID: Combines filters with vector search (default)
"""

import json
import logging
from typing import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from src.core.schemas import (
    PaperMetadata,
    QueryClassification,
    QueryRequest,
    QueryType,
    SearchMode,
    SearchRequest,
    StreamEvent,
    StreamEventType,
    StreamMetadata,
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


@router.post("/search")
async def search(request: SearchRequest) -> StreamingResponse:
    """
    Execute a search query with optional filters.

    Returns a Server-Sent Events (SSE) stream with:
    1. `metadata` event: Search results, filters, and other metadata (JSON)
    2. `chunk` events: LLM response text chunks
    3. `done` event: Stream completion signal

    Supports three search modes:
    - SEMANTIC: Vector similarity search only (requires query)
    - FILTER_ONLY: Payload filtering without vector search (requires filters)
    - HYBRID: Combines filters with vector search (default, requires query)

    For natural language queries: performs vector similarity search.
    For paper ID queries: looks up the paper and returns similar papers.
    Filters can be parsed automatically from the query or provided explicitly.

    Examples:
    - {"query": "neural machine translation"} - semantic search
    - {"filters": {"year": {"exact": 2017}}, "mode": "filter_only"} - filter only
    - {"query": "transformers", "filters": {"year": {"min_year": 2020}}} - hybrid
    - {"query": "papers about BERT by Devlin from 2019"} - auto-parsed filters
    """
    return StreamingResponse(
        generate_sse_stream(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


async def generate_sse_stream(request: SearchRequest) -> AsyncIterator[str]:
    """
    Generate Server-Sent Events stream for search response.

    SSE Format:
    - event: metadata\ndata: {...}\n\n  (first event with results/filters)
    - event: chunk\ndata: "text"\n\n     (response text chunks)
    - event: done\ndata: \n\n            (completion signal)
    """
    pipeline = get_pipeline()

    try:
        async for item in pipeline.search_stream(request):
            if isinstance(item, StreamMetadata):
                # Send metadata as JSON
                yield f"event: metadata\ndata: {item.model_dump_json()}\n\n"
            elif isinstance(item, StreamEvent):
                if item.event == StreamEventType.CHUNK:
                    # Send text chunk (escape newlines for SSE)
                    chunk_data = json.dumps(item.data) if item.data else '""'
                    yield f"event: chunk\ndata: {chunk_data}\n\n"
                elif item.event == StreamEventType.DONE:
                    yield f"event: done\ndata: \n\n"
    except Exception as e:
        logger.error(f"Streaming search failed: {e}", exc_info=True)
        # Send error event
        error_data = json.dumps({"error": str(e)})
        yield f"event: error\ndata: {error_data}\n\n"




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
