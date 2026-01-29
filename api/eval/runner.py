"""
Main evaluation orchestrator.

Runs the full evaluation pipeline: loads ground truth, executes each query
through the live pipeline, collects outputs, runs all metrics, saves results.

Usage:
    cd api
    python -m eval.scripts.run_eval --suite full
    python -m eval.scripts.run_eval --suite quick
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from eval.config import eval_config, RESULTS_DIR
from eval.dataset import GroundTruthDataset, load_ground_truth
from eval.metrics.retrieval import compute_all_retrieval_metrics
from eval.metrics.filter_parsing import evaluate_filter_parsing, aggregate_filter_metrics
from eval.metrics.latency import compute_stage_latencies, aggregate_latencies
from eval.metrics.generation import evaluate_all_generation_metrics
from eval.metrics.reformulation import evaluate_reformulation_quality

from src.core.schemas import (
    SearchRequest,
    StreamEvent,
    StreamEventType,
    StreamMetadata,
)
from src.retrieval.pipeline import RetrievalPipeline

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """
    Orchestrates the full evaluation pipeline.

    Supports two suites:
    - "quick": Retrieval + filter + latency metrics only (no LLM judge, free)
    - "full": All metrics including LLM judge (uses Groq 70B)
    """

    def __init__(
        self,
        suite: str = "full",
        categories: Optional[List[str]] = None,
        ground_truth_path: Optional[str] = None,
    ):
        self.suite = suite
        self.categories = categories
        self.dataset = load_ground_truth(ground_truth_path)
        self.pipeline = RetrievalPipeline()
        self.results: List[Dict[str, Any]] = []
        self.output_path: Optional[str] = None

    def _select_queries(self) -> List[Dict[str, Any]]:
        """Select queries based on configured categories."""
        if self.categories:
            return self.dataset.get_by_categories(self.categories)
        return list(self.dataset)

    async def run(self) -> Dict[str, Any]:
        """Run the full evaluation and return summary."""
        queries = self._select_queries()
        total = len(queries)

        logger.info(f"Starting {self.suite} evaluation with {total} queries")
        print(f"\nRunning {self.suite} evaluation on {total} queries...")

        for i, query_item in enumerate(queries, 1):
            query_id = query_item.get("id", f"unknown_{i}")
            query_text = query_item.get("query", "")
            category = query_item.get("category", "unknown")

            print(f"  [{i}/{total}] {category}/{query_id}: {query_text[:60]}...")

            try:
                result = await self._evaluate_single(query_item)
                self.results.append(result)
            except Exception as e:
                logger.error(f"Failed to evaluate {query_id}: {e}", exc_info=True)
                self.results.append({
                    "query_id": query_id,
                    "category": category,
                    "error": str(e),
                })

            # Rate limiting for Groq
            if self.suite == "full":
                await asyncio.sleep(eval_config.JUDGE_DELAY_SECONDS)

        summary = self._compute_summary()
        self._save_results(summary)

        print(f"\nEvaluation complete. Results saved to {self.output_path}")
        return summary

    async def _evaluate_single(self, query_item: Dict[str, Any]) -> Dict[str, Any]:
        """Run full evaluation for a single query."""
        query = query_item.get("query", "")
        query_id = query_item.get("id", "unknown")
        category = query_item.get("category", "unknown")
        expected_is_relevant = query_item.get("expected_is_relevant", True)

        result: Dict[str, Any] = {
            "query_id": query_id,
            "category": category,
            "query": query,
        }

        # Run the full pipeline via search_stream
        metadata: Optional[StreamMetadata] = None
        response_text = ""

        try:
            request = SearchRequest(query=query, top_k=eval_config.DEFAULT_TOP_K)

            async for item in self.pipeline.search_stream(request):
                if isinstance(item, StreamMetadata):
                    metadata = item
                elif isinstance(item, StreamEvent):
                    if item.event == StreamEventType.CHUNK and item.data:
                        response_text += item.data
        except Exception as e:
            logger.error(f"Pipeline failed for query '{query}': {e}")
            result["error"] = f"Pipeline error: {e}"
            return result

        if metadata is None:
            result["error"] = "No metadata received from pipeline"
            return result

        result["response_text"] = response_text
        result["num_results"] = len(metadata.results)
        result["is_relevant"] = metadata.is_relevant
        result["reformulated_queries"] = metadata.reformulated_queries

        # --- Filter parsing evaluation ---
        filter_eval = evaluate_filter_parsing(
            expected_filters=query_item.get("expected_filters"),
            actual_filters=metadata.parsed_filters,
            actual_is_relevant=metadata.is_relevant,
            expected_is_relevant=expected_is_relevant,
        )
        result["filter_eval"] = filter_eval

        # If the query was marked irrelevant, evaluate just the relevance classification
        if not metadata.is_relevant:
            result["correctly_rejected"] = not expected_is_relevant
            return result

        # --- Retrieval metrics ---
        relevant_ids = set(query_item.get("expected_relevant_paper_ids", []))
        retrieved_ids = [r.paper.paper_id for r in metadata.results]
        result["retrieved_paper_ids"] = retrieved_ids

        if relevant_ids:
            retrieval_metrics = compute_all_retrieval_metrics(
                retrieved_ids=retrieved_ids,
                relevant_ids=relevant_ids,
                k_values=eval_config.RETRIEVAL_K_VALUES,
            )
            result["retrieval_metrics"] = retrieval_metrics

        # --- Latency metrics ---
        if metadata.timestamps:
            result["latency"] = compute_stage_latencies(metadata.timestamps)

        # --- Generation metrics (only in full suite) ---
        if self.suite == "full" and response_text and metadata.results:
            papers_data = [r.paper.model_dump() for r in metadata.results]

            try:
                gen_metrics = await evaluate_all_generation_metrics(
                    query=query,
                    response=response_text,
                    papers=papers_data,
                )
                result["generation_metrics"] = gen_metrics
            except Exception as e:
                logger.error(f"Generation metrics failed for {query_id}: {e}")
                result["generation_metrics_error"] = str(e)

            # Rate limit between judge calls
            await asyncio.sleep(eval_config.JUDGE_DELAY_SECONDS)

            # --- Reformulation quality ---
            if metadata.reformulated_queries:
                try:
                    reform_quality = await evaluate_reformulation_quality(
                        original_query=query,
                        reformulated_queries=metadata.reformulated_queries,
                    )
                    result["reformulation_quality"] = reform_quality
                except Exception as e:
                    logger.error(f"Reformulation eval failed for {query_id}: {e}")
                    result["reformulation_quality_error"] = str(e)

        return result

    def _compute_summary(self) -> Dict[str, Any]:
        """Compute aggregate summary across all evaluated queries."""
        summary: Dict[str, Any] = {
            "suite": self.suite,
            "total_queries": len(self.results),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Aggregate by category
        categories: Dict[str, List[Dict]] = {}
        for r in self.results:
            cat = r.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        # --- Filter metrics ---
        filter_results = [r.get("filter_eval", {}) for r in self.results if "filter_eval" in r]
        summary["filter_metrics"] = aggregate_filter_metrics(filter_results)

        # --- Retrieval metrics (averaged across queries that have ground truth) ---
        retrieval_results = [
            r["retrieval_metrics"] for r in self.results if "retrieval_metrics" in r
        ]
        if retrieval_results:
            avg_retrieval: Dict[str, float] = {}
            for key in retrieval_results[0]:
                values = [r[key] for r in retrieval_results if key in r]
                avg_retrieval[key] = sum(values) / len(values) if values else 0
            summary["avg_retrieval_metrics"] = avg_retrieval

        # --- Latency metrics ---
        latencies = [r["latency"] for r in self.results if "latency" in r]
        if latencies:
            summary["latency_stats"] = aggregate_latencies(latencies)

        # --- Generation metrics (only in full suite) ---
        gen_results = [
            r["generation_metrics"] for r in self.results if "generation_metrics" in r
        ]
        if gen_results:
            avg_gen: Dict[str, float] = {}
            for metric_name in ["faithfulness", "answer_relevance", "groundedness"]:
                scores = [
                    r[metric_name]["score"]
                    for r in gen_results
                    if metric_name in r and "score" in r[metric_name]
                ]
                if scores:
                    avg_gen[f"avg_{metric_name}"] = sum(scores) / len(scores)
            summary["avg_generation_metrics"] = avg_gen

        # --- Reformulation quality ---
        reform_results = [
            r["reformulation_quality"]
            for r in self.results
            if "reformulation_quality" in r
        ]
        if reform_results:
            avg_reform: Dict[str, float] = {}
            for dim in ["fidelity", "diversity", "specificity", "domain_appropriateness", "overall"]:
                scores = [r[dim] for r in reform_results if dim in r and isinstance(r[dim], (int, float))]
                if scores:
                    avg_reform[f"avg_{dim}"] = sum(scores) / len(scores)
            summary["avg_reformulation_quality"] = avg_reform

        # --- Per-category breakdown ---
        category_summary: Dict[str, Any] = {}
        for cat, cat_results in categories.items():
            cat_summary: Dict[str, Any] = {"count": len(cat_results)}

            # Retrieval
            cat_retrieval = [r["retrieval_metrics"] for r in cat_results if "retrieval_metrics" in r]
            if cat_retrieval:
                cat_avg: Dict[str, float] = {}
                for key in cat_retrieval[0]:
                    vals = [r[key] for r in cat_retrieval if key in r]
                    cat_avg[key] = sum(vals) / len(vals) if vals else 0
                cat_summary["retrieval"] = cat_avg

            # Generation
            cat_gen = [r["generation_metrics"] for r in cat_results if "generation_metrics" in r]
            if cat_gen:
                for metric_name in ["faithfulness", "answer_relevance", "groundedness"]:
                    scores = [r[metric_name]["score"] for r in cat_gen if metric_name in r and "score" in r[metric_name]]
                    if scores:
                        cat_summary[f"avg_{metric_name}"] = sum(scores) / len(scores)

            # Latency
            cat_latencies = [r["latency"] for r in cat_results if "latency" in r]
            if cat_latencies:
                total_ms_vals = [l["total_ms"] for l in cat_latencies]
                cat_summary["avg_latency_ms"] = sum(total_ms_vals) / len(total_ms_vals)

            category_summary[cat] = cat_summary

        summary["per_category"] = category_summary

        # --- Irrelevance detection ---
        irrelevant_queries = [r for r in self.results if r.get("category") == "irrelevant"]
        if irrelevant_queries:
            correctly_rejected = sum(1 for r in irrelevant_queries if r.get("correctly_rejected", False))
            summary["irrelevance_detection"] = {
                "total": len(irrelevant_queries),
                "correctly_rejected": correctly_rejected,
                "accuracy": correctly_rejected / len(irrelevant_queries),
            }

        summary["individual_results"] = self.results

        return summary

    def _save_results(self, summary: Dict[str, Any]) -> None:
        """Save results to a timestamped JSON file."""
        results_dir = Path(RESULTS_DIR)
        results_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"eval_{self.suite}_{timestamp}.json"
        self.output_path = str(results_dir / filename)

        with open(self.output_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        # Also save as "latest.json" for easy access
        latest_path = results_dir / "latest.json"
        with open(latest_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        logger.info(f"Results saved to {self.output_path}")
