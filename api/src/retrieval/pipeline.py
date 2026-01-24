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

from src.core.config import settings
from src.core.schemas import (
    PaperMetadata,
    QueryType,
    SearchRequest,
    SearchResponse,
)
from src.llm.reformulator import get_reformulator, get_synthesizer
from src.retrieval.aggregator import get_aggregator
from src.retrieval.query_processor import (
    detect_query_type,
    QueryType as ProcessorQueryType,
)
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

        # Use singleton instances for reformulator, aggregator, and synthesizer
        self.reformulator = get_reformulator()
        self.aggregator = get_aggregator()
        self.synthesizer = get_synthesizer()

    @property
    def qdrant_client(self):
        """Get the Qdrant client from centralized components."""
        return self._components.qdrant_client

    async def _search_single_query(
        self,
        query: str,
        top_k: int,
    ) -> List[Tuple[PaperMetadata, float]]:
        """
        Execute a single vector search query using direct Qdrant API.

        Uses direct Qdrant client calls to properly retrieve payload fields
        since LangChain's QdrantVectorStore has specific expectations about
        payload structure (nested under 'metadata' key) that don't match
        our flat payload structure.

        Args:
            query: Search query string
            top_k: Number of results to return

        Returns:
            List of (PaperMetadata, score) tuples
        """
        # Get embedding for query using centralized embeddings
        query_vector = self._components.embeddings.embed_query(query)

        # Search directly via Qdrant client
        search_results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            with_payload=True,
        )

        results = []
        for point in search_results.points:
            payload = point.payload or {}
            paper = PaperMetadata(
                paper_id=payload.get("paper_id", ""),
                title=payload.get("title", ""),
                abstract=payload.get("abstract"),
                year=payload.get("year"),
                authors=payload.get("authors"),
                pdf_url=payload.get("pdf_url"),
            )
            # Qdrant returns cosine similarity score (higher = more similar)
            # Score is already in [0, 1] range for cosine similarity
            similarity = max(0.0, min(1.0, point.score))
            results.append((paper, similarity))

        return results

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

        Uses a scroll through all points to find exact match by paper_id.
        This is slower than indexed search but works without a payload index.

        Note: For production, create a keyword index on paper_id for better performance:
        client.create_payload_index(collection_name, "paper_id", PayloadSchemaType.KEYWORD)

        Args:
            paper_id: Normalized ACL paper identifier

        Returns:
            PaperMetadata if found, None otherwise
        """
        try:
            logger.debug(f"Looking up paper with ID: {paper_id}")

            # Scroll through points to find exact match
            # This is slow but works without a payload index
            offset = None
            while True:
                results = self.qdrant_client.scroll(
                    collection_name=self.collection_name,
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                points, next_offset = results

                for point in points:
                    payload = point.payload or {}
                    if payload.get("paper_id") == paper_id:
                        logger.debug(f"Found exact match for paper_id={paper_id}")
                        return PaperMetadata(
                            paper_id=payload.get("paper_id", paper_id),
                            title=payload.get("title", ""),
                            abstract=payload.get("abstract"),
                            year=payload.get("year"),
                            authors=payload.get("authors"),
                            pdf_url=payload.get("pdf_url"),
                        )

                if next_offset is None:
                    break
                offset = next_offset

            logger.warning(f"No exact match found for paper_id={paper_id}")
        except Exception as e:
            logger.error(f"Failed to fetch paper {paper_id}: {e}", exc_info=True)

        return None

    async def search(self, request: SearchRequest) -> SearchResponse:
        """
        Execute the full retrieval pipeline.

        Args:
            request: Search request with query and top_k

        Returns:
            SearchResponse with ranked results
        """
        # Step 1: Classify query type (use regex first, then LLM if needed)
        processor_query_type, paper_id = detect_query_type(request.query)
        source_paper: Optional[PaperMetadata] = None

        # Convert processor QueryType to schema QueryType
        is_paper_id_query = processor_query_type == ProcessorQueryType.PAPER_ID

        # Step 2: Get search queries (reformulation or paper-based)
        if is_paper_id_query and paper_id is not None:
            source_paper = await self._get_paper_by_id(paper_id)
            if source_paper and source_paper.abstract:
                queries = await self.reformulator.reformulate_from_paper(
                    title=source_paper.title,
                    abstract=source_paper.abstract,
                )
            else:
                # Paper not found in database
                return SearchResponse(
                    query_type=QueryType.PAPER_ID,
                    original_query=request.query,
                    paper_id=paper_id,
                    source_paper=None,
                    results=[],
                    response=f"I couldn't find paper **{paper_id}** in the ACL Anthology database. Please check the paper ID and try again.",
                )
        else:
            queries = await self.reformulator.reformulate(request.query)

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

        # Remove source paper from results if present (don't show it as similar to itself)
        if source_paper:
            final_results = [
                r for r in final_results if r.paper.paper_id != source_paper.paper_id
            ]

        # Step 6: Synthesize natural language response
        response = await self.synthesizer.synthesize(
            query=request.query,
            results=final_results,
            source_paper=source_paper,
        )

        return SearchResponse(
            query_type=(
                QueryType.PAPER_ID if is_paper_id_query else QueryType.NATURAL_LANGUAGE
            ),
            original_query=request.query,
            paper_id=paper_id if is_paper_id_query else None,
            source_paper=source_paper,
            results=final_results,
            response=response,
        )


# Module-level singleton
_pipeline: Optional[RetrievalPipeline] = None


def get_pipeline() -> RetrievalPipeline:
    """Get or create the singleton RetrievalPipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RetrievalPipeline()
    return _pipeline
