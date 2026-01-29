"""
Ablation study experiments for pipeline parameter tuning.

Supports four experiments:
A. Query reformulation count impact (0, 1, 2, 3, 4)
B. RRF weight tuning (score_weight x rrf_k grid)
C. Top-K impact (1, 3, 5, 10, 15, 20)
D. Filter parsing impact (with vs without)
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from eval.config import eval_config, RESULTS_DIR
from eval.dataset import load_ground_truth
from eval.metrics.retrieval import compute_all_retrieval_metrics
from eval.metrics.latency import compute_stage_latencies

from src.core.schemas import (
    PaperMetadata,
    SearchRequest,
    SearchResult,
    StreamEvent,
    StreamEventType,
    StreamMetadata,
)
from src.retrieval.aggregator import ResultAggregator
from src.retrieval.pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)


class AblationRunner:
    """Runs ablation experiments and saves results."""

    def __init__(self, ground_truth_path: Optional[str] = None):
        self.dataset = load_ground_truth(ground_truth_path)
        self.pipeline = RetrievalPipeline()

    def _get_eval_queries(self) -> List[Dict[str, Any]]:
        """Get queries that have ground truth paper IDs for retrieval evaluation."""
        return [
            q for q in self.dataset
            if q.get("expected_relevant_paper_ids")
            and q.get("expected_is_relevant", True)
        ]

    def _get_all_relevant_queries(self) -> List[Dict[str, Any]]:
        """Get all queries expected to be relevant (for general ablations)."""
        return [
            q for q in self.dataset
            if q.get("expected_is_relevant", True)
            and q.get("category") != "irrelevant"
        ]

    async def run_reformulation_ablation(self) -> Dict[str, Any]:
        """
        Experiment A: Impact of query reformulation count on retrieval quality.

        Tests NUM_REFORMULATED_QUERIES = {0, 1, 2, 3, 4}.
        When 0: skip reformulation, search only with original query.
        """
        print("\n=== Reformulation Ablation ===")
        queries = self._get_all_relevant_queries()
        results_by_count: Dict[int, List[Dict]] = {}

        for num_queries in eval_config.REFORMULATION_COUNTS:
            print(f"\n  Testing num_reformulated_queries={num_queries}...")
            run_results = []

            for i, query_item in enumerate(queries):
                query = query_item["query"]
                relevant_ids = set(query_item.get("expected_relevant_paper_ids", []))

                try:
                    # Parse filters first
                    parsed = await self.pipeline.filter_parser.parse(query)
                    if not parsed.is_relevant:
                        continue

                    semantic_query = parsed.semantic_query or query

                    # Build qdrant filter
                    qdrant_filter = None
                    if parsed.filters and not parsed.filters.is_empty():
                        qdrant_filter = self.pipeline.filter_builder.build(parsed.filters)

                    # Get search queries based on num_queries setting
                    if num_queries == 0:
                        search_queries = [semantic_query]
                    else:
                        original_num = self.pipeline.reformulator.num_queries
                        self.pipeline.reformulator.num_queries = num_queries
                        search_queries = await self.pipeline.reformulator.reformulate(semantic_query)
                        self.pipeline.reformulator.num_queries = original_num

                    # Search
                    per_query_k = eval_config.DEFAULT_TOP_K * self.pipeline.search_k_multiplier
                    start_time = time.time()
                    results_per_query = await self.pipeline._search_multiple_queries(
                        search_queries, per_query_k, qdrant_filter
                    )
                    search_time = (time.time() - start_time) * 1000

                    # Aggregate
                    if len(results_per_query) > 1:
                        final = self.pipeline.aggregator.aggregate(
                            results_per_query, top_k=eval_config.DEFAULT_TOP_K
                        )
                    elif len(results_per_query) == 1:
                        final = self.pipeline.aggregator.deduplicate_simple(
                            results_per_query[0], top_k=eval_config.DEFAULT_TOP_K
                        )
                    else:
                        final = []

                    retrieved_ids = [r.paper.paper_id for r in final]

                    entry: Dict[str, Any] = {
                        "query_id": query_item["id"],
                        "num_queries_used": len(search_queries),
                        "num_results": len(final),
                        "search_time_ms": search_time,
                    }

                    if relevant_ids:
                        entry["retrieval_metrics"] = compute_all_retrieval_metrics(
                            retrieved_ids, relevant_ids, [5]
                        )

                    run_results.append(entry)

                except Exception as e:
                    logger.error(f"Ablation failed for {query_item['id']}: {e}")

            results_by_count[num_queries] = run_results
            print(f"    Completed {len(run_results)} queries")

        return self._summarize_ablation("reformulation", results_by_count)

    async def run_rrf_ablation(self) -> Dict[str, Any]:
        """
        Experiment B: RRF weight tuning.

        Varies RRF_SCORE_WEIGHT and RRF_K in a grid search.
        Re-aggregates the same search results (no re-embedding needed).
        """
        print("\n=== RRF Weight Ablation ===")
        queries = self._get_all_relevant_queries()

        # First, collect raw search results for all queries
        print("  Collecting search results...")
        raw_results: List[Dict[str, Any]] = []

        for query_item in queries:
            query = query_item["query"]
            relevant_ids = set(query_item.get("expected_relevant_paper_ids", []))

            try:
                parsed = await self.pipeline.filter_parser.parse(query)
                if not parsed.is_relevant:
                    continue

                semantic_query = parsed.semantic_query or query
                qdrant_filter = None
                if parsed.filters and not parsed.filters.is_empty():
                    qdrant_filter = self.pipeline.filter_builder.build(parsed.filters)

                search_queries = await self.pipeline.reformulator.reformulate(semantic_query)
                per_query_k = eval_config.DEFAULT_TOP_K * self.pipeline.search_k_multiplier
                results_per_query = await self.pipeline._search_multiple_queries(
                    search_queries, per_query_k, qdrant_filter
                )

                if len(results_per_query) > 1:
                    raw_results.append({
                        "query_id": query_item["id"],
                        "results_per_query": results_per_query,
                        "relevant_ids": relevant_ids,
                    })

            except Exception as e:
                logger.error(f"RRF ablation pre-search failed for {query_item['id']}: {e}")

        print(f"  Collected {len(raw_results)} multi-query result sets")

        # Now re-aggregate with different parameters
        grid_results: Dict[str, Dict[str, Any]] = {}

        for score_weight in eval_config.RRF_SCORE_WEIGHTS:
            for rrf_k in eval_config.RRF_K_VALUES:
                key = f"sw={score_weight}_k={rrf_k}"
                print(f"  Testing {key}...")

                aggregator = ResultAggregator(k=rrf_k, score_weight=score_weight)
                param_results = []

                for raw in raw_results:
                    final = aggregator.aggregate(
                        raw["results_per_query"],
                        top_k=eval_config.DEFAULT_TOP_K,
                    )
                    retrieved_ids = [r.paper.paper_id for r in final]

                    if raw["relevant_ids"]:
                        metrics = compute_all_retrieval_metrics(
                            retrieved_ids, raw["relevant_ids"], [5]
                        )
                        param_results.append(metrics)

                if param_results:
                    avg_metrics: Dict[str, float] = {}
                    for metric_key in param_results[0]:
                        vals = [r[metric_key] for r in param_results]
                        avg_metrics[metric_key] = sum(vals) / len(vals)

                    grid_results[key] = {
                        "score_weight": score_weight,
                        "rrf_k": rrf_k,
                        "avg_metrics": avg_metrics,
                        "num_queries": len(param_results),
                    }

        return {
            "experiment": "rrf",
            "grid_results": grid_results,
            "num_raw_queries": len(raw_results),
        }

    async def run_topk_ablation(self) -> Dict[str, Any]:
        """
        Experiment C: Top-K impact on retrieval metrics.
        """
        print("\n=== Top-K Ablation ===")
        queries = self._get_all_relevant_queries()
        results_by_k: Dict[int, List[Dict]] = {}

        # Collect results with max top_k, then slice
        max_k = max(eval_config.TOP_K_VALUES)

        print(f"  Searching with top_k={max_k}...")
        all_results: List[Dict[str, Any]] = []

        for query_item in queries:
            query = query_item["query"]
            relevant_ids = set(query_item.get("expected_relevant_paper_ids", []))

            try:
                request = SearchRequest(query=query, top_k=min(max_k, 20))
                metadata = None
                async for item in self.pipeline.search_stream(request):
                    if isinstance(item, StreamMetadata):
                        metadata = item

                if metadata and metadata.results:
                    all_results.append({
                        "query_id": query_item["id"],
                        "retrieved_ids": [r.paper.paper_id for r in metadata.results],
                        "relevant_ids": relevant_ids,
                    })
            except Exception as e:
                logger.error(f"Top-K ablation failed for {query_item['id']}: {e}")

        # Evaluate at each k value
        for k in eval_config.TOP_K_VALUES:
            k_results = []
            for result_data in all_results:
                if result_data["relevant_ids"]:
                    sliced_ids = result_data["retrieved_ids"][:k]
                    metrics = compute_all_retrieval_metrics(
                        sliced_ids, result_data["relevant_ids"], [k]
                    )
                    k_results.append(metrics)
            results_by_k[k] = k_results

        # Summarize
        summary: Dict[str, Any] = {"experiment": "topk", "results": {}}
        for k, k_results in results_by_k.items():
            if k_results:
                avg: Dict[str, float] = {}
                for metric_key in k_results[0]:
                    vals = [r[metric_key] for r in k_results]
                    avg[metric_key] = sum(vals) / len(vals)
                summary["results"][str(k)] = {
                    "avg_metrics": avg,
                    "num_queries": len(k_results),
                }

        return summary

    async def run_filter_ablation(self) -> Dict[str, Any]:
        """
        Experiment D: Filter parsing impact.

        Compares results with vs without filter parsing for filtered queries only.
        """
        print("\n=== Filter Parsing Ablation ===")
        filtered_queries = self.dataset.get_by_category("filtered")

        if not filtered_queries:
            return {"experiment": "filter", "error": "No filtered queries in dataset"}

        with_filter_results = []
        without_filter_results = []

        for query_item in filtered_queries:
            query = query_item["query"]
            relevant_ids = set(query_item.get("expected_relevant_paper_ids", []))

            try:
                # --- With filters ---
                request = SearchRequest(query=query, top_k=eval_config.DEFAULT_TOP_K)
                metadata_with = None
                async for item in self.pipeline.search_stream(request):
                    if isinstance(item, StreamMetadata):
                        metadata_with = item

                if metadata_with:
                    ids_with = [r.paper.paper_id for r in metadata_with.results]
                    with_filter_results.append({
                        "query_id": query_item["id"],
                        "retrieved_ids": ids_with,
                        "num_results": len(ids_with),
                        "relevant_ids": relevant_ids,
                    })

                # --- Without filters (bypass filter parsing) ---
                search_queries = await self.pipeline.reformulator.reformulate(query)
                per_query_k = eval_config.DEFAULT_TOP_K * self.pipeline.search_k_multiplier
                results_per_query = await self.pipeline._search_multiple_queries(
                    search_queries, per_query_k, None  # No filter
                )

                if len(results_per_query) > 1:
                    final = self.pipeline.aggregator.aggregate(
                        results_per_query, top_k=eval_config.DEFAULT_TOP_K
                    )
                elif len(results_per_query) == 1:
                    final = self.pipeline.aggregator.deduplicate_simple(
                        results_per_query[0], top_k=eval_config.DEFAULT_TOP_K
                    )
                else:
                    final = []

                ids_without = [r.paper.paper_id for r in final]
                without_filter_results.append({
                    "query_id": query_item["id"],
                    "retrieved_ids": ids_without,
                    "num_results": len(ids_without),
                    "relevant_ids": relevant_ids,
                })

            except Exception as e:
                logger.error(f"Filter ablation failed for {query_item['id']}: {e}")

        return {
            "experiment": "filter",
            "with_filters": with_filter_results,
            "without_filters": without_filter_results,
            "num_queries": len(filtered_queries),
        }

    def _summarize_ablation(
        self, experiment_name: str, results_by_param: Dict[Any, List[Dict]]
    ) -> Dict[str, Any]:
        """Summarize ablation results by averaging metrics."""
        summary: Dict[str, Any] = {
            "experiment": experiment_name,
            "results": {},
        }

        for param_value, param_results in results_by_param.items():
            with_metrics = [r for r in param_results if "retrieval_metrics" in r]

            if with_metrics:
                avg_metrics: Dict[str, float] = {}
                for key in with_metrics[0]["retrieval_metrics"]:
                    vals = [r["retrieval_metrics"][key] for r in with_metrics]
                    avg_metrics[key] = sum(vals) / len(vals)

                avg_search_time = sum(r.get("search_time_ms", 0) for r in param_results) / len(param_results)

                summary["results"][str(param_value)] = {
                    "avg_metrics": avg_metrics,
                    "avg_search_time_ms": avg_search_time,
                    "num_queries": len(param_results),
                    "num_with_ground_truth": len(with_metrics),
                }
            else:
                summary["results"][str(param_value)] = {
                    "num_queries": len(param_results),
                    "num_with_ground_truth": 0,
                }

        return summary

    async def run_all(self) -> Dict[str, Any]:
        """Run all ablation experiments."""
        all_results: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        print("Running all ablation experiments...")

        all_results["reformulation"] = await self.run_reformulation_ablation()
        all_results["rrf"] = await self.run_rrf_ablation()
        all_results["topk"] = await self.run_topk_ablation()
        all_results["filter"] = await self.run_filter_ablation()

        # Save results
        results_dir = Path(RESULTS_DIR)
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_path = results_dir / f"ablation_{timestamp}.json"

        with open(output_path, "w") as f:
            json.dump(all_results, f, indent=2, default=str)

        print(f"\nAblation results saved to {output_path}")
        return all_results
