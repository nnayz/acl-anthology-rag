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
    ParsedQuery,
    QueryType,
    SearchFilters,
    SearchMode,
    SearchRequest,
    SearchResponse,
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
    QueryType as ProcessorQueryType,
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

    async def _search_filter_only(
        self,
        qdrant_filter: Filter,
        top_k: int,
    ) -> List[Tuple[PaperMetadata, float]]:
        """
        Execute a filter-only search (no vector similarity).

        Args:
            qdrant_filter: Qdrant filter to apply
            top_k: Number of results to return

        Returns:
            List of (PaperMetadata, score) tuples (score is always 1.0)
        """
        points = self._components.scroll_with_filter(
            filter=qdrant_filter,
            limit=top_k,
            collection_name=self.collection_name,
        )

        results = []
        for point in points:
            payload = point.payload or {}
            paper = PaperMetadata(
                paper_id=payload.get("paper_id", ""),
                title=payload.get("title", ""),
                abstract=payload.get("abstract"),
                year=payload.get("year"),
                authors=payload.get("authors"),
                pdf_url=payload.get("pdf_url"),
            )
            # Filter-only searches don't have relevance scores
            results.append((paper, 1.0))

        return results

    def _merge_filters(
        self,
        explicit_filters: Optional[SearchFilters],
        parsed_filters: Optional[SearchFilters],
    ) -> Optional[SearchFilters]:
        """
        Merge explicit filters with parsed filters.

        Explicit filters take precedence over parsed filters.

        Args:
            explicit_filters: Filters provided explicitly in the request
            parsed_filters: Filters extracted from the query

        Returns:
            Merged SearchFilters or None if both are empty
        """
        if not explicit_filters and not parsed_filters:
            return None

        if not explicit_filters:
            return parsed_filters

        if not parsed_filters:
            return explicit_filters

        # Merge: explicit takes precedence
        return SearchFilters(
            year=explicit_filters.year or parsed_filters.year,
            bibkey=explicit_filters.bibkey or parsed_filters.bibkey,
            title_keywords=explicit_filters.title_keywords or parsed_filters.title_keywords,
            language=explicit_filters.language or parsed_filters.language,
            authors=explicit_filters.authors or parsed_filters.authors,
            has_awards=(
                explicit_filters.has_awards
                if explicit_filters.has_awards is not None
                else parsed_filters.has_awards
            ),
            awards=explicit_filters.awards or parsed_filters.awards,
        )

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

        Handles three search modes:
        - SEMANTIC: Vector search only
        - FILTER_ONLY: Payload filtering without vector search
        - HYBRID: Combines filters with vector search

        Args:
            request: Search request with query, filters, and mode

        Returns:
            SearchResponse with ranked results
        """
        original_query = request.query or ""
        parsed_filters: Optional[SearchFilters] = None
        semantic_query: Optional[str] = original_query

        # Step 1: Parse filters from query if enabled
        if request.parse_filters_from_query and original_query:
            parsed_query = await self.filter_parser.parse(original_query)
            parsed_filters = parsed_query.filters
            # Use the semantic query extracted by the LLM (stripped of filter words)
            if parsed_query.semantic_query:
                semantic_query = parsed_query.semantic_query
            elif parsed_filters and not parsed_filters.is_empty():
                # If filters were found but no semantic query, set to None
                semantic_query = None

        # Step 2: Merge explicit filters with parsed filters
        applied_filters = self._merge_filters(request.filters, parsed_filters)

        # Build Qdrant filter
        qdrant_filter: Optional[Filter] = None
        if applied_filters and not applied_filters.is_empty():
            qdrant_filter = self.filter_builder.build(applied_filters)
            logger.debug(f"Built Qdrant filter: {qdrant_filter}")

        # Determine effective mode based on what we have
        effective_mode = request.mode
        if request.mode == SearchMode.HYBRID:
            if not semantic_query and qdrant_filter:
                effective_mode = SearchMode.FILTER_ONLY
            elif semantic_query and not qdrant_filter:
                effective_mode = SearchMode.SEMANTIC

        # Step 3: Handle FILTER_ONLY mode
        if effective_mode == SearchMode.FILTER_ONLY:
            if not qdrant_filter:
                return SearchResponse(
                    query_type=QueryType.NATURAL_LANGUAGE,
                    original_query=original_query,
                    results=[],
                    response="No filters could be applied. Please provide specific filters or a search query.",
                    mode=effective_mode,
                    parsed_filters=parsed_filters,
                    applied_filters=applied_filters,
                )

            results_tuples = await self._search_filter_only(
                qdrant_filter=qdrant_filter,
                top_k=request.top_k,
            )
            final_results = [
                SearchResult(paper=paper, score=score)
                for paper, score in results_tuples
            ]

            # Generate response for filter-only results
            response = await self.synthesizer.synthesize(
                query=original_query or "Filter search",
                results=final_results,
                source_paper=None,
            )

            return SearchResponse(
                query_type=QueryType.NATURAL_LANGUAGE,
                original_query=original_query,
                results=final_results,
                response=response,
                mode=effective_mode,
                parsed_filters=parsed_filters,
                applied_filters=applied_filters,
            )

        # Step 4: Handle SEMANTIC or HYBRID modes
        # Use semantic_query for searching (might be cleaned up version of original)
        search_query = semantic_query or original_query

        # Check for paper ID query
        processor_query_type, paper_id = detect_query_type(search_query)
        source_paper: Optional[PaperMetadata] = None
        is_paper_id_query = processor_query_type == ProcessorQueryType.PAPER_ID

        # Step 5: Get search queries (reformulation or paper-based)
        if is_paper_id_query and paper_id is not None:
            source_paper = await self._get_paper_by_id(paper_id)
            if source_paper and source_paper.abstract:
                queries = await self.reformulator.reformulate_from_paper(
                    title=source_paper.title,
                    abstract=source_paper.abstract,
                )
            else:
                return SearchResponse(
                    query_type=QueryType.PAPER_ID,
                    original_query=original_query,
                    paper_id=paper_id,
                    source_paper=None,
                    results=[],
                    response=f"I couldn't find paper **{paper_id}** in the ACL Anthology database. Please check the paper ID and try again.",
                    mode=effective_mode,
                    parsed_filters=parsed_filters,
                    applied_filters=applied_filters,
                )
        else:
            queries = await self.reformulator.reformulate(search_query)

        logger.debug(f"Reformulated into {len(queries)} queries: {queries}")

        # Step 6: Embed and search for each query (with optional filter)
        per_query_k = request.top_k * self.search_k_multiplier
        results_per_query = await self._search_multiple_queries(
            queries, per_query_k, qdrant_filter
        )

        # Step 7: Aggregate results
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

        # Remove source paper from results if present
        if source_paper:
            final_results = [
                r for r in final_results if r.paper.paper_id != source_paper.paper_id
            ]

        # Step 8: Synthesize natural language response
        response = await self.synthesizer.synthesize(
            query=original_query or search_query,
            results=final_results,
            source_paper=source_paper,
        )

        return SearchResponse(
            query_type=(
                QueryType.PAPER_ID if is_paper_id_query else QueryType.NATURAL_LANGUAGE
            ),
            original_query=original_query,
            paper_id=paper_id if is_paper_id_query else None,
            source_paper=source_paper,
            results=final_results,
            response=response,
            mode=effective_mode,
            parsed_filters=parsed_filters,
            applied_filters=applied_filters,
        )

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
        
        original_query = request.query or ""
        parsed_filters: Optional[SearchFilters] = None
        semantic_query: Optional[str] = original_query

        # Step 1: Parse filters from query if enabled
        if request.parse_filters_from_query and original_query:
            parsed_query = await self.filter_parser.parse(original_query)
            parsed_filters = parsed_query.filters
            timestamps["filterParsed"] = time.time()
            
            if parsed_query.semantic_query:
                semantic_query = parsed_query.semantic_query
            elif parsed_filters and not parsed_filters.is_empty():
                semantic_query = None

        # Step 2: Merge explicit filters with parsed filters
        applied_filters = self._merge_filters(request.filters, parsed_filters)

        # Build Qdrant filter
        qdrant_filter: Optional[Filter] = None
        if applied_filters and not applied_filters.is_empty():
            qdrant_filter = self.filter_builder.build(applied_filters)

        # Determine effective mode
        effective_mode = request.mode
        if request.mode == SearchMode.HYBRID:
            if not semantic_query and qdrant_filter:
                effective_mode = SearchMode.FILTER_ONLY
            elif semantic_query and not qdrant_filter:
                effective_mode = SearchMode.SEMANTIC

        # Step 3: Handle FILTER_ONLY mode
        if effective_mode == SearchMode.FILTER_ONLY:
            if not qdrant_filter:
                yield StreamMetadata(
                    query_type=QueryType.NATURAL_LANGUAGE,
                    original_query=original_query,
                    results=[],
                    mode=effective_mode,
                    parsed_filters=parsed_filters,
                    applied_filters=applied_filters,
                    semantic_query=semantic_query,
                    reformulated_queries=[],
                    timestamps=timestamps,
                )
                yield StreamEvent(
                    event=StreamEventType.CHUNK,
                    data="No filters could be applied. Please provide specific filters or a search query.",
                )
                yield StreamEvent(event=StreamEventType.DONE)
                return

            results_tuples = await self._search_filter_only(
                qdrant_filter=qdrant_filter,
                top_k=request.top_k,
            )
            timestamps["searchCompleted"] = time.time()
            
            final_results = [
                SearchResult(paper=paper, score=score)
                for paper, score in results_tuples
            ]

            # Yield metadata first
            yield StreamMetadata(
                query_type=QueryType.NATURAL_LANGUAGE,
                original_query=original_query,
                results=final_results,
                mode=effective_mode,
                parsed_filters=parsed_filters,
                applied_filters=applied_filters,
                semantic_query=semantic_query,
                reformulated_queries=[],
                timestamps=timestamps,
            )

            # Stream the response
            async for chunk in self.synthesizer.synthesize_stream(
                query=original_query or "Filter search",
                results=final_results,
                source_paper=None,
            ):
                yield StreamEvent(event=StreamEventType.CHUNK, data=chunk)

            timestamps["responseGenerated"] = time.time()
            yield StreamEvent(event=StreamEventType.DONE)
            return

        # Step 4: Handle SEMANTIC or HYBRID modes
        search_query = semantic_query or original_query
        processor_query_type, paper_id = detect_query_type(search_query)
        source_paper: Optional[PaperMetadata] = None
        is_paper_id_query = processor_query_type == ProcessorQueryType.PAPER_ID

        # Step 5: Get search queries
        if is_paper_id_query and paper_id is not None:
            source_paper = await self._get_paper_by_id(paper_id)
            if source_paper and source_paper.abstract:
                queries = await self.reformulator.reformulate_from_paper(
                    title=source_paper.title,
                    abstract=source_paper.abstract,
                )
            else:
                yield StreamMetadata(
                    query_type=QueryType.PAPER_ID,
                    original_query=original_query,
                    results=[],
                    paper_id=paper_id,
                    mode=effective_mode,
                    parsed_filters=parsed_filters,
                    applied_filters=applied_filters,
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

        # Step 6: Embed and search
        per_query_k = request.top_k * self.search_k_multiplier
        results_per_query = await self._search_multiple_queries(
            queries, per_query_k, qdrant_filter
        )

        # Step 7: Aggregate results
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
            query_type=(
                QueryType.PAPER_ID if is_paper_id_query else QueryType.NATURAL_LANGUAGE
            ),
            original_query=original_query,
            results=final_results,
            paper_id=paper_id if is_paper_id_query else None,
            source_paper=source_paper,
            mode=effective_mode,
            parsed_filters=parsed_filters,
            applied_filters=applied_filters,
            semantic_query=semantic_query,
            reformulated_queries=queries,
            timestamps=timestamps,
        )

        # Step 8: Stream the synthesized response
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
