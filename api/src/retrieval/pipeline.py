"""
Retrieval pipeline orchestration.

This module coordinates the full query processing workflow:
Query -> Filter Parsing -> Reformulation -> Embedding -> Vector Search -> Aggregation

It provides the main entry point for executing searches against
the ACL Anthology corpus using LangChain components.

The pipeline is designed as a composable chain that:
1. Parses filters from natural language query (optional)
2. Classifies the query type (natural language vs paper ID)
3. Reformulates into multiple search queries via LLM
4. Embeds and searches each query sequentially
5. Aggregates results using Reciprocal Rank Fusion

Supports three search modes:
- SEMANTIC: Vector search only (default behavior)
- FILTER_ONLY: Payload filtering without vector search
- HYBRID: Combines filters with vector search
"""

import logging
import time
from typing import AsyncIterator, List, Optional, Tuple, Union

from qdrant_client.models import Filter

from src.core.config import settings
from src.core.schemas import (
    PaperMetadata,
    SearchFilters,
    SearchRequest,
    SearchResult,
    StreamEvent,
    StreamEventType,
    StreamMetadata,
)
from src.llm.reformulator import get_reformulator, get_synthesizer
from src.retrieval.aggregator import get_aggregator
from src.retrieval.filter_builder import get_filter_builder
from src.retrieval.filter_parser import get_filter_parser
from src.retrieval.query_processor import (
    detect_query_type,
)
from src.vectorstore.client import get_langchain_components

logger = logging.getLogger(__name__)


class RetrievalPipeline:
    """
    Orchestrates the full retrieval pipeline for semantic search.

    Uses centralized LangChain components for efficient multi-query retrieval.

    The pipeline follows this flow:
    1. Parse filters from query (if enabled)
    2. Query classification (natural language vs paper ID)
    3. Query reformulation (LLM expands to multiple queries)
    4. Sequential embedding + vector search (with optional filters)
    5. Result aggregation (RRF fusion + deduplication)

    Supports three search modes:
    - SEMANTIC: Vector search only
    - FILTER_ONLY: Payload filtering without vector search
    - HYBRID: Combines filters with vector search (default)

    Attributes:
        collection_name: Name of the Qdrant collection
        search_k_multiplier: Multiplier for per-query results
        components: Centralized LangChain components
        reformulator: Query reformulation LLM chain
        aggregator: Result aggregation logic
        filter_parser: LLM-based filter extraction
        filter_builder: Qdrant filter construction
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

        # Filter handling components
        self.filter_parser = get_filter_parser()
        self.filter_builder = get_filter_builder()

    @property
    def qdrant_client(self):
        """Get the Qdrant client from centralized components."""
        return self._components.qdrant_client

    async def _search_single_query(
        self,
        query: str,
        top_k: int,
        qdrant_filter: Optional[Filter] = None,
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
            qdrant_filter: Optional Qdrant filter to apply

        Returns:
            List of (PaperMetadata, score) tuples
        """
        # Get embedding for query using centralized embeddings
        query_vector = self._components.embeddings.embed_query(query)

        # Search directly via Qdrant client (with optional filter)
        search_results = self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=qdrant_filter,
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
        qdrant_filter: Optional[Filter] = None,
    ) -> List[List[Tuple[PaperMetadata, float]]]:
        """
        Execute multiple vector searches sequentially.

        Note: HuggingFace embeddings model is not thread-safe for concurrent
        embedding operations, so searches must run sequentially.

        Args:
            queries: List of search queries
            top_k: Number of results per query
            qdrant_filter: Optional Qdrant filter to apply to all queries

        Returns:
            List of result lists, one per query
        """
        results = []
        for query in queries:
            try:
                result = await self._search_single_query(query, top_k, qdrant_filter)
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

    async def search_stream(
        self, request: SearchRequest
    ) -> AsyncIterator[Union[StreamMetadata, StreamEvent]]:
        """
        Execute streaming search - yields metadata first, then response chunks.

        This method performs the same search as search() but streams the
        LLM-generated response instead of waiting for it to complete.

        Yields:
            First: StreamMetadata with search results and metadata
            Then: StreamEvent objects with response chunks
            Finally: StreamEvent with event=DONE

        Args:
            request: Search request with query, filters, and mode
        """
        # Initialize monitoring timestamps
        timestamps = {"start": time.time()}

        original_query = request.query  # Validation handled by pydantic model validator
        parsed_filters: Optional[SearchFilters] = None
        semantic_query: Optional[str] = original_query

        # Parse filters from query
        parsed_query = await self.filter_parser.parse(original_query)
        parsed_filters = parsed_query.filters
        timestamps["filterParsed"] = time.time()

        # Handle irrelevant queries early
        if not parsed_query.is_relevant:
            yield StreamMetadata(
                original_query=original_query,
                results=[],
                parsed_filters=None,
                is_relevant=False,
                semantic_query=None,
                reformulated_queries=[],
                timestamps=timestamps,
            )
            yield StreamEvent(
                event=StreamEventType.CHUNK,
                data=parsed_query.irrelevant_response
                or "I can only help with academic paper searches.",
            )
            yield StreamEvent(event=StreamEventType.DONE)
            return

        if parsed_query.semantic_query:
            semantic_query = parsed_query.semantic_query
        elif parsed_filters and not parsed_filters.is_empty():
            semantic_query = None

        # Build Qdrant filter
        qdrant_filter: Optional[Filter] = None
        if parsed_filters and not parsed_filters.is_empty():
            qdrant_filter = self.filter_builder.build(parsed_filters)

        # Detect paper ID query and get search queries
        search_query = semantic_query or original_query
        processor_query_type, paper_id = detect_query_type(search_query)
        source_paper: Optional[PaperMetadata] = None
        is_paper_id_query = processor_query_type.value == "paper_id"

        # Get search queries
        if is_paper_id_query and paper_id is not None:
            source_paper = await self._get_paper_by_id(paper_id)
            if source_paper and source_paper.abstract:
                queries = await self.reformulator.reformulate_from_paper(
                    title=source_paper.title,
                    abstract=source_paper.abstract,
                )
            else:
                yield StreamMetadata(
                    original_query=original_query,
                    results=[],
                    paper_id=paper_id,
                    parsed_filters=parsed_filters,
                    semantic_query=semantic_query,
                    reformulated_queries=[],
                    timestamps=timestamps,
                )
                yield StreamEvent(
                    event=StreamEventType.CHUNK,
                    data=f"I couldn't find paper **{paper_id}** in the ACL Anthology database. Please check the paper ID and try again.",
                )
                yield StreamEvent(event=StreamEventType.DONE)
                return
        else:
            queries = await self.reformulator.reformulate(search_query)

        timestamps["queriesReformed"] = time.time()

        # Embed and search
        per_query_k = request.top_k * self.search_k_multiplier
        results_per_query = await self._search_multiple_queries(
            queries, per_query_k, qdrant_filter
        )

        # Aggregate results
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

        timestamps["searchCompleted"] = time.time()

        # Remove source paper from results
        if source_paper:
            final_results = [
                r for r in final_results if r.paper.paper_id != source_paper.paper_id
            ]

        # Yield metadata first
        yield StreamMetadata(
            original_query=original_query,
            results=final_results,
            paper_id=paper_id if is_paper_id_query else None,
            source_paper=source_paper,
            parsed_filters=parsed_filters,
            semantic_query=semantic_query,
            reformulated_queries=queries,
            timestamps=timestamps,
        )

        # Stream the synthesized response
        async for chunk in self.synthesizer.synthesize_stream(
            query=original_query or search_query,
            results=final_results,
            source_paper=source_paper,
        ):
            yield StreamEvent(event=StreamEventType.CHUNK, data=chunk)

        timestamps["responseGenerated"] = time.time()
        yield StreamEvent(event=StreamEventType.DONE)


# Module-level singleton
_pipeline: Optional[RetrievalPipeline] = None


def get_pipeline() -> RetrievalPipeline:
    """Get or create the singleton RetrievalPipeline instance."""
    global _pipeline
    if _pipeline is None:
        _pipeline = RetrievalPipeline()
    return _pipeline
