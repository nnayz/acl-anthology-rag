"""
CLI entry point for running ablation experiments.

Usage:
    cd api
    python -m eval.scripts.run_ablation --experiment all
    python -m eval.scripts.run_ablation --experiment reformulation
    python -m eval.scripts.run_ablation --experiment rrf
    python -m eval.scripts.run_ablation --experiment topk
    python -m eval.scripts.run_ablation --experiment filter
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from eval.ablations.runner import AblationRunner


def main():
    parser = argparse.ArgumentParser(
        description="Run ablation experiments for RAG pipeline"
    )
    parser.add_argument(
        "--experiment",
        choices=["all", "reformulation", "rrf", "topk", "filter"],
        default="all",
        help="Which ablation experiment to run",
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        default=None,
        help="Path to ground truth JSON file",
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

    runner = AblationRunner(ground_truth_path=args.ground_truth)

    if args.experiment == "all":
        results = asyncio.run(runner.run_all())
    elif args.experiment == "reformulation":
        results = asyncio.run(runner.run_reformulation_ablation())
    elif args.experiment == "rrf":
        results = asyncio.run(runner.run_rrf_ablation())
    elif args.experiment == "topk":
        results = asyncio.run(runner.run_topk_ablation())
    elif args.experiment == "filter":
        results = asyncio.run(runner.run_filter_ablation())

    print("\nAblation experiment complete.")


if __name__ == "__main__":
    main()
