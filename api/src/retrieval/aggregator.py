"""
Result aggregation and ranking.

This module merges results from multiple query embeddings and
produces a final ranked list of relevant papers. Aggregation
strategies include score fusion and deduplication.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from src.core.config import settings
from src.core.schemas import PaperMetadata, SearchResult


class ResultAggregator:
    """
    Aggregates search results from multiple queries into a single ranked list.

    Implements Reciprocal Rank Fusion (RRF) for combining results from
    multiple queries, which is effective when result scores from different
    queries are not directly comparable.

    Attributes:
        k: RRF constant (default from settings)
        score_weight: Weight given to original similarity scores vs rank
    """

    def __init__(
        self,
        k: Optional[int] = None,
        score_weight: Optional[float] = None,
    ):
        """
        Initialize the aggregator.

        Args:
            k: RRF constant - higher values give more weight to lower ranks (default: from settings)
            score_weight: Weight for score-based fusion (0-1) (default: from settings)
        """
        self.k = k if k is not None else settings.RRF_K
        self.score_weight = score_weight if score_weight is not None else settings.RRF_SCORE_WEIGHT

    def aggregate(
        self,
        results_per_query: List[List[Tuple[PaperMetadata, float]]],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Aggregate results from multiple queries using hybrid RRF + score fusion.

        Args:
            results_per_query: List of result lists, each containing
                              (PaperMetadata, score) tuples
            top_k: Number of final results to return

        Returns:
            Deduplicated and ranked list of SearchResults
        """
        if not results_per_query:
            return []

        # Track both RRF scores and raw scores for each paper
        paper_rrf_scores: Dict[str, float] = defaultdict(float)
        paper_raw_scores: Dict[str, List[float]] = defaultdict(list)
        paper_metadata: Dict[str, PaperMetadata] = {}

        # Process each query's results
        for query_results in results_per_query:
            for rank, (paper, score) in enumerate(query_results, start=1):
                paper_id = paper.paper_id

                # RRF score contribution
                paper_rrf_scores[paper_id] += 1.0 / (self.k + rank)

                # Track raw scores for averaging
                paper_raw_scores[paper_id].append(score)

                # Store metadata (last occurrence wins, but they should be identical)
                paper_metadata[paper_id] = paper

        # Compute final scores using hybrid approach
        final_scores: List[Tuple[str, float]] = []

        for paper_id in paper_rrf_scores:
            rrf_score = paper_rrf_scores[paper_id]
            avg_raw_score = sum(paper_raw_scores[paper_id]) / len(paper_raw_scores[paper_id])

            # Normalize RRF score to [0, 1] range (approximate)
            # Max possible RRF for a paper appearing at rank 1 in all queries
            max_rrf = len(results_per_query) / (self.k + 1)
            normalized_rrf = rrf_score / max_rrf if max_rrf > 0 else 0

            # Hybrid score
            final_score = (
                self.score_weight * avg_raw_score +
                (1 - self.score_weight) * normalized_rrf
            )

            final_scores.append((paper_id, final_score))

        # Sort by final score descending
        final_scores.sort(key=lambda x: x[1], reverse=True)

        # Build final result list
        results = []
        for paper_id, score in final_scores[:top_k]:
            results.append(SearchResult(
                paper=paper_metadata[paper_id],
                score=min(score, 1.0),  # Clamp to [0, 1]
            ))

        return results

    def deduplicate_simple(
        self,
        results: List[Tuple[PaperMetadata, float]],
        top_k: int = 10,
    ) -> List[SearchResult]:
        """
        Simple deduplication by paper_id, keeping highest score.

        Useful when only one query is used (no multi-query fusion needed).

        Args:
            results: List of (PaperMetadata, score) tuples
            top_k: Number of results to return

        Returns:
            Deduplicated SearchResult list
        """
        seen: Dict[str, SearchResult] = {}

        for paper, score in results:
            paper_id = paper.paper_id
            if paper_id not in seen or score > seen[paper_id].score:
                seen[paper_id] = SearchResult(paper=paper, score=score)

        # Sort by score and return top_k
        sorted_results = sorted(seen.values(), key=lambda r: r.score, reverse=True)
        return sorted_results[:top_k]


# Module-level singleton
_aggregator: Optional[ResultAggregator] = None


def get_aggregator() -> ResultAggregator:
    """Get or create the singleton ResultAggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = ResultAggregator()
    return _aggregator
