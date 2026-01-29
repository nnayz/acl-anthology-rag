"""
Report generation with charts and tables for evaluation results.

Generates matplotlib/seaborn charts and formatted tables from evaluation
results for use in class presentations.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_import_plotting():
    """Import plotting libraries with graceful fallback."""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        sns.set_theme(style="whitegrid", palette="muted")
        return plt, sns
    except ImportError:
        logger.error("matplotlib/seaborn not installed. Run: pip install matplotlib seaborn")
        raise


def _safe_import_pandas():
    """Import pandas with graceful fallback."""
    try:
        import pandas as pd
        return pd
    except ImportError:
        logger.error("pandas not installed. Run: pip install pandas")
        raise


def generate_retrieval_by_category_chart(
    results: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Chart 1: Grouped bar chart of retrieval metrics by query category.
    """
    plt, sns = _safe_import_plotting()
    pd = _safe_import_pandas()

    per_category = results.get("per_category", {})
    if not per_category:
        logger.warning("No per-category data available for chart")
        return

    rows = []
    for cat, cat_data in per_category.items():
        retrieval = cat_data.get("retrieval", {})
        if retrieval:
            rows.append({
                "Category": cat,
                "P@5": retrieval.get("precision@5", 0),
                "R@5": retrieval.get("recall@5", 0),
                "MRR": retrieval.get("mrr", 0),
                "NDCG@5": retrieval.get("ndcg@5", 0),
            })

    if not rows:
        logger.warning("No retrieval metrics to chart")
        return

    df = pd.DataFrame(rows)
    df_melted = df.melt(id_vars="Category", var_name="Metric", value_name="Score")

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=df_melted, x="Category", y="Score", hue="Metric", ax=ax)
    ax.set_title("Retrieval Metrics by Query Category", fontsize=14, fontweight="bold")
    ax.set_ylabel("Score")
    ax.set_ylim(0, 1.05)
    ax.legend(title="Metric", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_reformulation_ablation_chart(
    ablation_results: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Chart 2: Line chart showing impact of reformulation count on metrics.
    """
    plt, sns = _safe_import_plotting()

    reform_data = ablation_results.get("reformulation", {}).get("results", {})
    if not reform_data:
        logger.warning("No reformulation ablation data")
        return

    x_vals = []
    metrics_data: Dict[str, List[float]] = {
        "P@5": [], "R@5": [], "MRR": [], "NDCG@5": []
    }

    for num_str in sorted(reform_data.keys(), key=int):
        entry = reform_data[num_str]
        avg = entry.get("avg_metrics", {})
        if avg:
            x_vals.append(int(num_str))
            metrics_data["P@5"].append(avg.get("precision@5", 0))
            metrics_data["R@5"].append(avg.get("recall@5", 0))
            metrics_data["MRR"].append(avg.get("mrr", 0))
            metrics_data["NDCG@5"].append(avg.get("ndcg@5", 0))

    if not x_vals:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    for metric_name, values in metrics_data.items():
        ax.plot(x_vals, values, marker="o", linewidth=2, label=metric_name)

    ax.set_xlabel("Number of Reformulated Queries", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Impact of Query Reformulation on Retrieval Quality", fontsize=14, fontweight="bold")
    ax.set_xticks(x_vals)
    ax.set_ylim(0, 1.05)
    ax.legend(title="Metric")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_latency_breakdown_chart(
    results: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Chart 3: Stacked bar chart showing latency breakdown per pipeline stage.
    """
    plt, sns = _safe_import_plotting()
    pd = _safe_import_pandas()

    latency_stats = results.get("latency_stats", {})
    if not latency_stats:
        logger.warning("No latency data available")
        return

    stages = ["filter_parsing_ms", "query_reformulation_ms", "vector_search_ms", "response_synthesis_ms"]
    labels = ["Filter\nParsing", "Query\nReformulation", "Vector\nSearch", "Response\nSynthesis"]
    means = [latency_stats.get(s, {}).get("mean", 0) for s in stages]

    fig, ax = plt.subplots(figsize=(10, 6))
    colors = sns.color_palette("muted", len(stages))
    bars = ax.bar(labels, means, color=colors, edgecolor="white", linewidth=1.5)

    # Add value labels on bars
    for bar, val in zip(bars, means):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 10,
                f"{val:.0f}ms", ha="center", va="bottom", fontsize=11, fontweight="bold")

    ax.set_ylabel("Latency (ms)", fontsize=12)
    ax.set_title("Average Pipeline Latency Breakdown", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_rrf_heatmap(
    ablation_results: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Chart 4: Heatmap of NDCG@5 across RRF parameter grid.
    """
    plt, sns = _safe_import_plotting()
    pd = _safe_import_pandas()

    rrf_data = ablation_results.get("rrf", {}).get("grid_results", {})
    if not rrf_data:
        logger.warning("No RRF ablation data")
        return

    rows = []
    for key, entry in rrf_data.items():
        avg = entry.get("avg_metrics", {})
        rows.append({
            "Score Weight": entry.get("score_weight", 0),
            "RRF K": entry.get("rrf_k", 0),
            "NDCG@5": avg.get("ndcg@5", 0),
        })

    if not rows:
        return

    df = pd.DataFrame(rows)
    pivot = df.pivot(index="Score Weight", columns="RRF K", values="NDCG@5")

    fig, ax = plt.subplots(figsize=(10, 7))
    sns.heatmap(pivot, annot=True, fmt=".3f", cmap="YlOrRd", ax=ax,
                cbar_kws={"label": "NDCG@5"})
    ax.set_title("RRF Parameter Grid Search (NDCG@5)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_topk_chart(
    ablation_results: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Chart 5: Top-K vs quality trade-off line chart.
    """
    plt, sns = _safe_import_plotting()

    topk_data = ablation_results.get("topk", {}).get("results", {})
    if not topk_data:
        logger.warning("No top-k ablation data")
        return

    k_vals = []
    hit_rates = []
    mrr_vals = []

    for k_str in sorted(topk_data.keys(), key=int):
        entry = topk_data[k_str]
        avg = entry.get("avg_metrics", {})
        if avg:
            k_vals.append(int(k_str))
            hit_rates.append(avg.get(f"hit_rate@{k_str}", 0))
            mrr_vals.append(avg.get("mrr", 0))

    if not k_vals:
        return

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(k_vals, hit_rates, marker="s", linewidth=2, label="Hit Rate@k", color="steelblue")
    ax.plot(k_vals, mrr_vals, marker="o", linewidth=2, label="MRR", color="coral")

    ax.set_xlabel("Top-K", fontsize=12)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title("Impact of Top-K on Retrieval Quality", fontsize=14, fontweight="bold")
    ax.set_xticks(k_vals)
    ax.set_ylim(0, 1.05)
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_irrelevance_confusion_matrix(
    results: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Chart 6: Confusion matrix for irrelevance detection.
    """
    plt, sns = _safe_import_plotting()

    individual = results.get("individual_results", [])
    if not individual:
        return

    # Build confusion matrix
    tp = fp = tn = fn = 0
    for r in individual:
        expected_relevant = r.get("category") != "irrelevant"
        actual_relevant = r.get("is_relevant", True)

        if expected_relevant and actual_relevant:
            tp += 1
        elif expected_relevant and not actual_relevant:
            fn += 1
        elif not expected_relevant and actual_relevant:
            fp += 1
        else:
            tn += 1

    matrix = [[tp, fn], [fp, tn]]
    labels = [["TP\n(Correctly\nRelevant)", "FN\n(Missed\nRelevant)"],
              ["FP\n(Missed\nIrrelevant)", "TN\n(Correctly\nIrrelevant)"]]

    fig, ax = plt.subplots(figsize=(7, 6))
    sns.heatmap(matrix, annot=False, fmt="d", cmap="Blues", ax=ax,
                xticklabels=["Predicted\nRelevant", "Predicted\nIrrelevant"],
                yticklabels=["Actually\nRelevant", "Actually\nIrrelevant"])

    # Add text annotations with counts and labels
    for i in range(2):
        for j in range(2):
            ax.text(j + 0.5, i + 0.5,
                    f"{labels[i][j]}\n({matrix[i][j]})",
                    ha="center", va="center", fontsize=11, fontweight="bold")

    ax.set_title("Relevance Classification Confusion Matrix", fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def generate_summary_table(results: Dict[str, Any]) -> str:
    """Generate a formatted summary table string."""
    pd = _safe_import_pandas()

    per_category = results.get("per_category", {})
    rows = []

    for cat, data in per_category.items():
        row: Dict[str, Any] = {"Category": cat, "Count": data.get("count", 0)}

        retrieval = data.get("retrieval", {})
        row["P@5"] = f"{retrieval.get('precision@5', 0):.3f}" if retrieval else "N/A"
        row["R@5"] = f"{retrieval.get('recall@5', 0):.3f}" if retrieval else "N/A"
        row["MRR"] = f"{retrieval.get('mrr', 0):.3f}" if retrieval else "N/A"
        row["NDCG@5"] = f"{retrieval.get('ndcg@5', 0):.3f}" if retrieval else "N/A"

        row["Faith."] = f"{data.get('avg_faithfulness', 0):.3f}" if "avg_faithfulness" in data else "N/A"
        row["Relev."] = f"{data.get('avg_answer_relevance', 0):.3f}" if "avg_answer_relevance" in data else "N/A"
        row["Ground."] = f"{data.get('avg_groundedness', 0):.3f}" if "avg_groundedness" in data else "N/A"

        row["Avg Latency"] = f"{data.get('avg_latency_ms', 0):.0f}ms" if "avg_latency_ms" in data else "N/A"

        rows.append(row)

    if not rows:
        return "No category data available."

    df = pd.DataFrame(rows)

    try:
        from tabulate import tabulate
        return tabulate(df, headers="keys", tablefmt="github", showindex=False)
    except ImportError:
        return df.to_string(index=False)


def generate_all_charts(
    eval_results_path: str,
    ablation_results_path: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> None:
    """Generate all charts from evaluation results."""
    output = Path(output_dir or Path(eval_results_path).parent)
    output.mkdir(parents=True, exist_ok=True)

    with open(eval_results_path) as f:
        eval_results = json.load(f)

    print("\nGenerating evaluation charts...")

    generate_retrieval_by_category_chart(
        eval_results, str(output / "retrieval_by_category.png")
    )
    generate_latency_breakdown_chart(
        eval_results, str(output / "latency_breakdown.png")
    )
    generate_irrelevance_confusion_matrix(
        eval_results, str(output / "confusion_matrix.png")
    )

    if ablation_results_path:
        with open(ablation_results_path) as f:
            ablation_results = json.load(f)

        print("\nGenerating ablation charts...")
        generate_reformulation_ablation_chart(
            ablation_results, str(output / "reformulation_ablation.png")
        )
        generate_rrf_heatmap(
            ablation_results, str(output / "rrf_heatmap.png")
        )
        generate_topk_chart(
            ablation_results, str(output / "topk_tradeoff.png")
        )

    # Print summary table
    print("\n" + generate_summary_table(eval_results))

    # Save summary table as CSV
    pd = _safe_import_pandas()
    per_category = eval_results.get("per_category", {})
    if per_category:
        rows = []
        for cat, data in per_category.items():
            row = {"category": cat, **data.get("retrieval", {})}
            for key in ["avg_faithfulness", "avg_answer_relevance", "avg_groundedness", "avg_latency_ms"]:
                if key in data:
                    row[key] = data[key]
            rows.append(row)
        df = pd.DataFrame(rows)
        csv_path = output / "summary_table.csv"
        df.to_csv(csv_path, index=False)
        print(f"\n  Saved: {csv_path}")
