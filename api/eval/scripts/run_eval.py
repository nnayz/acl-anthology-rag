"""
CLI entry point for running the evaluation pipeline.

Usage:
    cd api
    python -m eval.scripts.run_eval --suite full
    python -m eval.scripts.run_eval --suite quick
    python -m eval.scripts.run_eval --suite full --categories simple_factual,filtered
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add api/ to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from eval.runner import EvaluationRunner


def main():
    parser = argparse.ArgumentParser(
        description="Run ACL Anthology RAG evaluation pipeline"
    )
    parser.add_argument(
        "--suite",
        choices=["full", "quick"],
        default="full",
        help="Evaluation suite: 'full' (all metrics + LLM judge) or 'quick' (retrieval + filter + latency only)",
    )
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated list of query categories to evaluate (default: all)",
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        default=None,
        help="Path to ground truth JSON file (default: eval/data/ground_truth.json)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    categories = args.categories.split(",") if args.categories else None

    runner = EvaluationRunner(
        suite=args.suite,
        categories=categories,
        ground_truth_path=args.ground_truth,
    )

    results = asyncio.run(runner.run())

    # Print key metrics
    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    if "avg_retrieval_metrics" in results:
        print("\nRetrieval Metrics (averaged):")
        for key, val in results["avg_retrieval_metrics"].items():
            print(f"  {key}: {val:.3f}")

    if "avg_generation_metrics" in results:
        print("\nGeneration Metrics (averaged):")
        for key, val in results["avg_generation_metrics"].items():
            print(f"  {key}: {val:.3f}")

    if "avg_reformulation_quality" in results:
        print("\nReformulation Quality (averaged):")
        for key, val in results["avg_reformulation_quality"].items():
            print(f"  {key}: {val:.3f}")

    if "filter_metrics" in results:
        fm = results["filter_metrics"]
        print(f"\nFilter Parsing Accuracy:")
        print(f"  Relevance classification: {fm.get('relevance_accuracy', 0):.1%}")
        print(f"  Filter match: {fm.get('filter_match_accuracy', 0):.1%}")
        for field, acc in fm.get("field_accuracy", {}).items():
            print(f"  {field}: {acc:.1%}")

    if "irrelevance_detection" in results:
        ir = results["irrelevance_detection"]
        print(f"\nIrrelevance Detection:")
        print(f"  Accuracy: {ir.get('accuracy', 0):.1%} ({ir.get('correctly_rejected', 0)}/{ir.get('total', 0)})")

    if "latency_stats" in results:
        print("\nLatency (mean):")
        for stage, stats in results["latency_stats"].items():
            print(f"  {stage}: {stats.get('mean', 0):.0f}ms")

    print(f"\nResults saved to: {runner.output_path}")


if __name__ == "__main__":
    main()
