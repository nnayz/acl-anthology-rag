"""
CLI entry point for generating evaluation reports (charts + tables).

Usage:
    cd api
    python -m eval.scripts.generate_report
    python -m eval.scripts.generate_report --eval-results eval/data/results/latest.json
    python -m eval.scripts.generate_report --eval-results eval/data/results/latest.json --ablation-results eval/data/results/ablation_*.json
    python -m eval.scripts.generate_report --output-dir eval/data/results/charts
"""

import argparse
import glob
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from eval.reports.visualizer import generate_all_charts, generate_summary_table
from eval.config import RESULTS_DIR


def main():
    parser = argparse.ArgumentParser(
        description="Generate evaluation report charts and tables"
    )
    parser.add_argument(
        "--eval-results",
        type=str,
        default=None,
        help="Path to evaluation results JSON (default: latest.json)",
    )
    parser.add_argument(
        "--ablation-results",
        type=str,
        default=None,
        help="Path to ablation results JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for charts (default: same as results)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Find eval results
    eval_path = args.eval_results
    if eval_path is None:
        eval_path = str(Path(RESULTS_DIR) / "latest.json")
        if not Path(eval_path).exists():
            # Try to find most recent eval file
            pattern = str(Path(RESULTS_DIR) / "eval_*.json")
            files = sorted(glob.glob(pattern))
            if files:
                eval_path = files[-1]
            else:
                print(f"No evaluation results found in {RESULTS_DIR}")
                print("Run the evaluation first: python -m eval.scripts.run_eval")
                sys.exit(1)

    if not Path(eval_path).exists():
        print(f"Evaluation results not found: {eval_path}")
        sys.exit(1)

    # Find ablation results
    ablation_path = args.ablation_results
    if ablation_path is None:
        pattern = str(Path(RESULTS_DIR) / "ablation_*.json")
        files = sorted(glob.glob(pattern))
        if files:
            ablation_path = files[-1]

    output_dir = args.output_dir or str(Path(eval_path).parent)

    print(f"Evaluation results: {eval_path}")
    if ablation_path:
        print(f"Ablation results: {ablation_path}")
    print(f"Output directory: {output_dir}")

    generate_all_charts(
        eval_results_path=eval_path,
        ablation_results_path=ablation_path,
        output_dir=output_dir,
    )

    print("\nReport generation complete!")


if __name__ == "__main__":
    main()
