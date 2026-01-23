"""
API route definitions.

This module defines the HTTP endpoints for the retrieval system:
- POST /search - Execute a semantic search query
- GET /paper/{acl_id} - Fetch paper metadata by ACL ID
"""
"""
API route definitions.

This module defines the HTTP endpoints for the retrieval system:
- POST /search - Execute a semantic search query
- GET /paper/{acl_id} - Fetch paper metadata by ACL ID
"""

from fastapi import APIRouter, HTTPException, status

from src.retrieval.embedding import embed_query
from src.retrieval.qdrant_store import (
    fetch_paper_by_id,
    search_similar,
)
from src.core.schemas import (
    PaperMetadata,
    QueryClassification,
    QueryRequest,
    QueryType,
    SearchRequest,
    SearchResponse,
)
from src.retrieval.query_processor import detect_query_type, is_valid_acl_id

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/classify", response_model=QueryClassification)
async def classify_query(request: QueryRequest) -> QueryClassification:
    """
    Classify a user query to determine its type.
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
    query_type, paper_id = detect_query_type(request.query)

    # Decide text to embed
    if query_type == QueryType.PAPER_ID:
        paper = fetch_paper_by_id(paper_id)
        if paper is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Paper not found: {paper_id}",
            )
        text_to_embed = paper["abstract"]
    else:
        text_to_embed = request.query

    # Embed
    embedding = embed_query(text_to_embed)

    # Similarity search
    results = search_similar(
        embedding=embedding,
        top_k=request.top_k,
    )

    return SearchResponse(
        query_type=QueryType(query_type.value),
        original_query=request.query,
        paper_id=paper_id,
        results=results,
    )


@router.get("/paper/{paper_id}", response_model=PaperMetadata)
async def get_paper(paper_id: str) -> PaperMetadata:
    """
    Fetch paper metadata by ACL paper ID.
    """
    if not is_valid_acl_id(paper_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid ACL paper ID format: {paper_id}",
        )

    paper = fetch_paper_by_id(paper_id)

    if paper is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Paper not found: {paper_id}",
        )

    return PaperMetadata(**paper)
