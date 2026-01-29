"""
Retrieval quality metrics computed against ground truth relevance judgments.

All metrics compare retrieved paper IDs against known relevant paper IDs.
These are deterministic -- no LLM judge needed.
"""

import math
from typing import Dict, List, Set


def precision_at_k(
    retrieved_ids: List[str], relevant_ids: Set[str], k: int
) -> float:
    """Fraction of top-k results that are relevant."""
    top_k = retrieved_ids[:k]
    if not top_k:
        return 0.0
    relevant_in_top_k = sum(1 for pid in top_k if pid in relevant_ids)
    return relevant_in_top_k / k


def recall_at_k(
    retrieved_ids: List[str], relevant_ids: Set[str], k: int
) -> float:
    """Fraction of relevant documents found in top-k."""
    if not relevant_ids:
        return 1.0  # vacuously true
    top_k = retrieved_ids[:k]
    relevant_in_top_k = sum(1 for pid in top_k if pid in relevant_ids)
    return relevant_in_top_k / len(relevant_ids)


def mrr(retrieved_ids: List[str], relevant_ids: Set[str]) -> float:
    """Mean Reciprocal Rank: 1/rank of the first relevant result."""
    for i, pid in enumerate(retrieved_ids):
        if pid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(
    retrieved_ids: List[str], relevant_ids: Set[str], k: int
) -> float:
    """Normalized Discounted Cumulative Gain at k."""
    dcg = 0.0
    for i, pid in enumerate(retrieved_ids[:k]):
        rel = 1.0 if pid in relevant_ids else 0.0
        dcg += rel / math.log2(i + 2)  # +2 because i starts at 0

    # Ideal DCG: all relevant docs ranked at the top
    ideal_count = min(len(relevant_ids), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_count))

    return dcg / idcg if idcg > 0 else 0.0


def hit_rate_at_k(
    retrieved_ids: List[str], relevant_ids: Set[str], k: int
) -> float:
    """Binary: is at least one relevant doc in top-k? Returns 0 or 1."""
    top_k = retrieved_ids[:k]
    return 1.0 if any(pid in relevant_ids for pid in top_k) else 0.0


def compute_all_retrieval_metrics(
    retrieved_ids: List[str],
    relevant_ids: Set[str],
    k_values: List[int],
) -> Dict[str, float]:
    """Compute all retrieval metrics at multiple k values."""
    metrics: Dict[str, float] = {}

    for k in k_values:
        metrics[f"precision@{k}"] = precision_at_k(retrieved_ids, relevant_ids, k)
        metrics[f"recall@{k}"] = recall_at_k(retrieved_ids, relevant_ids, k)
        metrics[f"ndcg@{k}"] = ndcg_at_k(retrieved_ids, relevant_ids, k)
        metrics[f"hit_rate@{k}"] = hit_rate_at_k(retrieved_ids, relevant_ids, k)

    metrics["mrr"] = mrr(retrieved_ids, relevant_ids)

    return metrics
