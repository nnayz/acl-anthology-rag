"""
Latency analysis using timestamps already collected by the pipeline.

The pipeline tracks these timestamps in StreamMetadata.timestamps:
  - start: pipeline entry
  - filterParsed: after filter extraction LLM call
  - queriesReformed: after reformulation LLM call
  - searchCompleted: after all vector searches + aggregation
  - responseGenerated: after full LLM response streaming
"""

import statistics
from typing import Dict, List, Optional


def compute_stage_latencies(timestamps: Dict[str, float]) -> Dict[str, float]:
    """
    Compute per-stage latency from pipeline timestamps.

    Args:
        timestamps: Dict with start, filterParsed, queriesReformed,
                    searchCompleted, responseGenerated (all in epoch seconds)

    Returns:
        Dict with per-stage latencies in milliseconds
    """
    start = timestamps.get("start", 0)
    filter_parsed = timestamps.get("filterParsed", start)
    queries_reformed = timestamps.get("queriesReformed", filter_parsed)
    search_completed = timestamps.get("searchCompleted", queries_reformed)
    response_generated = timestamps.get("responseGenerated", search_completed)

    return {
        "filter_parsing_ms": (filter_parsed - start) * 1000,
        "query_reformulation_ms": (queries_reformed - filter_parsed) * 1000,
        "vector_search_ms": (search_completed - queries_reformed) * 1000,
        "response_synthesis_ms": (response_generated - search_completed) * 1000,
        "total_ms": (response_generated - start) * 1000,
    }


def aggregate_latencies(
    all_latencies: List[Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    """
    Compute aggregate stats (mean, median, p95, min, max) across all queries.

    Args:
        all_latencies: List of per-query latency dicts from compute_stage_latencies

    Returns:
        Dict mapping stage name -> {mean, median, p95, min, max}
    """
    if not all_latencies:
        return {}

    stages = all_latencies[0].keys()
    aggregated: Dict[str, Dict[str, float]] = {}

    for stage in stages:
        values = [lat[stage] for lat in all_latencies if stage in lat]
        if not values:
            continue

        sorted_values = sorted(values)
        p95_idx = min(int(len(sorted_values) * 0.95), len(sorted_values) - 1)

        aggregated[stage] = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "p95": sorted_values[p95_idx],
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }

    return aggregated


def format_latency_report(aggregated: Dict[str, Dict[str, float]]) -> str:
    """Format aggregated latencies as a readable report string."""
    lines = ["Pipeline Latency Report", "=" * 60]

    stage_labels = {
        "filter_parsing_ms": "Filter Parsing",
        "query_reformulation_ms": "Query Reformulation",
        "vector_search_ms": "Vector Search",
        "response_synthesis_ms": "Response Synthesis",
        "total_ms": "Total Pipeline",
    }

    for stage_key, label in stage_labels.items():
        if stage_key not in aggregated:
            continue
        stats = aggregated[stage_key]
        lines.append(f"\n{label}:")
        lines.append(f"  Mean:   {stats['mean']:>8.1f} ms")
        lines.append(f"  Median: {stats['median']:>8.1f} ms")
        lines.append(f"  P95:    {stats['p95']:>8.1f} ms")
        lines.append(f"  Min:    {stats['min']:>8.1f} ms")
        lines.append(f"  Max:    {stats['max']:>8.1f} ms")

    return "\n".join(lines)
