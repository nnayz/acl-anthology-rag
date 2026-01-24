"""
Retrieval pipeline orchestration.

This module coordinates the full query processing workflow:
Query -> Reformulation -> Embedding -> Vector Search -> Aggregation

It provides the main entry point for executing searches against
the ACL Anthology corpus using LangChain components.

The pipeline is designed as a composable chain that:
1. Classifies the query type (natural language vs paper ID)
2. Reformulates into multiple search queries via LLM
3. Embeds and searches each query sequentially
4. Aggregates results using Reciprocal Rank Fusion
"""

import logging
from typing import List, Optional, Tuple

from langchain_core.runnables import RunnableLambda
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.core.config import settings
from src.core.schemas import (
    PaperMetadata,
    QueryType,
    SearchRequest,
    SearchResponse,
)
from src.llm.reformulator import get_reformulator
from src.retrieval.aggregator import get_aggregator
from src.retrieval.query_processor import detect_query_type
from src.vectorstore.client import get_langchain_components

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """
    Orchestrates the full retrieval pipeline for semantic search.

    Uses centralized LangChain components for efficient multi-query retrieval.

    The pipeline follows this flow:
    1. Query classification (natural language vs paper ID)
    2. Query reformulation (LLM expands to multiple queries)
    3. Sequential embedding + vector search
    4. Result aggregation (RRF fusion + deduplication)

    Attributes:
        collection_name: Name of the Qdrant collection
        search_k_multiplier: Multiplier for per-query results
        components: Centralized LangChain components
        reformulator: Query reformulation LLM chain
        aggregator: Result aggregation logic
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        search_k_multiplier: Optional[int] = None,
    ):
        """
        Initialize the retrieval pipeline.

        Args:
            collection_name: Name of the existing Qdrant collection (default: from settings)
            search_k_multiplier: Multiplier for per-query results (default: from settings)
        """
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.search_k_multiplier = search_k_multiplier or settings.SEARCH_K_MULTIPLIER

        # Use centralized LangChain components
        self._components = get_langchain_components()

        # Use singleton instances for reformulator and aggregator
        self.reformulator = get_reformulator()
        self.aggregator = get_aggregator()

        # Build LangChain runnable for document parsing
        self._parse_result = RunnableLambda(self._parse_search_result)

    @property
    def vectorstore(self):
        """Get the vector store from centralized components."""
        return self._components.get_vectorstore(self.collection_name)

    @property
    def qdrant_client(self):
        """Get the Qdrant client from centralized components."""
        return self._components.qdrant_client

    @staticmethod
    def _parse_search_result(doc_score_tuple) -> Tuple[PaperMetadata, float]:
        """
        Parse a LangChain document into PaperMetadata.

        Args:
            doc_score_tuple: Tuple of (Document, score) from vector search

        Returns:
            Tuple of (PaperMetadata, similarity_score)
        """
        doc, score = doc_score_tuple
        metadata = doc.metadata
        paper = PaperMetadata(
            paper_id=metadata.get("paper_id", ""),
            title=metadata.get("title", ""),
            abstract=metadata.get("abstract"),
            year=metadata.get("year"),
            authors=metadata.get("authors"),
            pdf_url=metadata.get("pdf_url"),
        )
        # Qdrant cosine distance: lower = more similar
        # Convert to similarity: 1 - distance
        similarity = max(0.0, min(1.0, 1.0 - score))
        return (paper, similarity)

    async def _search_single_query(
        self,
        query: str,
        top_k: int,
    ) -> List[Tuple[PaperMetadata, float]]:
        """
        Execute a single vector search query.

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of (PaperMetadata, score) tuples
        """
        results = await self.vectorstore.asimilarity_search_with_score(
            query=query,
            k=top_k,
        )
        return [self._parse_search_result(r) for r in results]

    async def _search_multiple_queries(
        self,
        queries: List[str],
        top_k: int,
    ) -> List[List[Tuple[PaperMetadata, float]]]:
        """
        Execute multiple vector searches sequentially.

        Note: HuggingFace embeddings model is not thread-safe for concurrent
        embedding operations, so searches must run sequentially.

        Args:
            queries: List of search queries
            top_k: Number of results per query

        Returns:
            List of result lists, one per query
        """
        results = []
        for query in queries:
            try:
                result = await self._search_single_query(query, top_k)
                results.append(result)
            except Exception as e:
                logger.error(f"Search failed for query '{query}': {e}")

        return results

    async def _get_paper_by_id(self, paper_id: str) -> Optional[PaperMetadata]:
        """
        Fetch a paper's metadata by its ACL ID.

        Args:
            paper_id: Normalized ACL paper identifier

        Returns:
            PaperMetadata if found, None otherwise
        """
        try:
            results = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",
                            match=MatchValue(value=paper_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )

            points, _ = results
            if points:
                payload = points[0].payload
                return PaperMetadata(
                    paper_id=payload.get("paper_id", paper_id),
                    title=payload.get("title", ""),
                    abstract=payload.get("abstract"),
                    year=payload.get("year"),
                    authors=payload.get("authors"),
                    pdf_url=payload.get("pdf_url"),
                )
        except Exception as e:
            logger.error(f"Failed to fetch paper {paper_id}: {e}")

        return None

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute the full retrieval pipeline.

        Args:
            request: Search request with query and top_k

        Returns:
            SearchResponse with ranked results
        """
        # Step 1: Classify query type
        query_type, paper_id = detect_query_type(request.query)

        # Step 2: Get search queries (reformulation or paper-based)
        if query_type == QueryType.PAPER_ID and paper_id is not None:
            paper = await self._get_paper_by_id(paper_id)
            if paper and paper.abstract:
                queries = await self.reformulator.reformulate_from_paper(
                    title=paper.title,
                    abstract=paper.abstract,
                )
            else:
                return SearchResponse(
                    query_type=QueryType(query_type.value),
                    original_query=request.query,
                    paper_id=paper_id,
                    results=[],
                )
        else:
            queries = await self.reformulator.reformulate(request.query)
            print(f"[DEBUG] Reformulated queries: {queries}")

        logger.debug(f"Reformulated into {len(queries)} queries: {queries}")

        # Step 3 & 4: Embed and search for each query
        per_query_k = request.top_k * self.search_k_multiplier
        results_per_query = await self._search_multiple_queries(queries, per_query_k)

        # Step 5: Aggregate results
        if len(results_per_query) == 1:
            final_results = self.aggregator.deduplicate_simple(
                results_per_query[0],
                top_k=request.top_k,
            )
        elif len(results_per_query) > 1:
            final_results = self.aggregator.aggregate(
                results_per_query,
                top_k=request.top_k,
            )
        else:
            final_results = []

        return SearchResponse(
            query_type=QueryType(query_type.value),
            original_query=request.query,
            paper_id=paper_id if query_type == QueryType.PAPER_ID else None,
            results=final_results,
        )


# Module-level singleton
_pipeline: Optional[RetrievalPipeline] = None


def get_pipeline() -> RetrievalPipeline:
    """Get or create the singleton RetrievalPipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RetrievalPipeline()
    return _pipeline
