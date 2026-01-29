"""
Filter parsing accuracy metrics.

Deterministic comparison of expected vs actual filter extraction.
No LLM judge needed -- compares structured filter objects directly.
"""

from typing import Any, Dict, List, Optional


def evaluate_filter_parsing(
    expected_filters: Optional[Dict[str, Any]],
    actual_filters: Optional[Any],  # SearchFilters or None
    actual_is_relevant: bool,
    expected_is_relevant: bool,
) -> Dict[str, Any]:
    """
    Compare expected filter extraction against actual ParsedQuery output.

    Args:
        expected_filters: Expected filter dict from ground truth (or None)
        actual_filters: Actual SearchFilters object from pipeline (or None)
        actual_is_relevant: Whether pipeline classified query as relevant
        expected_is_relevant: Whether query should be classified as relevant

    Returns:
        Dict with relevance_correct, filter_match, field_level_accuracy
    """
    results: Dict[str, Any] = {}

    # 1. Relevance classification accuracy
    results["relevance_correct"] = actual_is_relevant == expected_is_relevant

    # If expected irrelevant, that's all we check
    if not expected_is_relevant:
        results["filter_match"] = True  # N/A for irrelevant queries
        results["field_level_accuracy"] = {}
        return results

    # 2. If no filters expected and none extracted
    if expected_filters is None and actual_filters is None:
        results["filter_match"] = True
        results["field_level_accuracy"] = {}
        return results

    # 3. If no filters expected but some extracted
    if expected_filters is None and actual_filters is not None:
        is_empty = actual_filters.is_empty() if hasattr(actual_filters, "is_empty") else True
        results["filter_match"] = is_empty
        results["field_level_accuracy"] = {}
        return results

    # 4. If filters expected but none extracted
    if expected_filters is not None and actual_filters is None:
        results["filter_match"] = False
        results["field_level_accuracy"] = {k: False for k in expected_filters}
        return results

    # 5. Compare each expected field
    field_results: Dict[str, bool] = {}

    for field_name, expected_value in expected_filters.items():
        actual_value = getattr(actual_filters, field_name, None)

        if field_name == "year" and expected_value is not None:
            if actual_value is None:
                field_results["year"] = False
            else:
                field_results["year"] = (
                    getattr(actual_value, "exact", None) == expected_value.get("exact")
                    and getattr(actual_value, "min_year", None)
                    == expected_value.get("min_year")
                    and getattr(actual_value, "max_year", None)
                    == expected_value.get("max_year")
                )
        elif field_name == "authors" and expected_value is not None:
            # Authors: check if expected authors are found (case-insensitive substring)
            if actual_value is None:
                field_results["authors"] = False
            else:
                actual_lower = [a.lower() for a in actual_value]
                expected_lower = [a.lower() for a in expected_value]
                field_results["authors"] = all(
                    any(exp in act for act in actual_lower) for exp in expected_lower
                )
        elif isinstance(expected_value, list):
            if actual_value is None:
                field_results[field_name] = False
            else:
                # Check if all expected items are present
                actual_set = set(
                    str(v).lower() for v in actual_value
                ) if actual_value else set()
                expected_set = set(str(v).lower() for v in expected_value)
                field_results[field_name] = expected_set.issubset(actual_set)
        else:
            field_results[field_name] = actual_value == expected_value

    results["field_level_accuracy"] = field_results
    results["filter_match"] = all(field_results.values()) if field_results else True

    return results


def aggregate_filter_metrics(
    all_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Aggregate filter parsing results across all queries."""
    if not all_results:
        return {}

    total = len(all_results)
    relevance_correct = sum(1 for r in all_results if r.get("relevance_correct", False))
    filter_match = sum(1 for r in all_results if r.get("filter_match", False))

    # Per-field accuracy
    field_counts: Dict[str, Dict[str, int]] = {}
    for result in all_results:
        for field, correct in result.get("field_level_accuracy", {}).items():
            if field not in field_counts:
                field_counts[field] = {"correct": 0, "total": 0}
            field_counts[field]["total"] += 1
            if correct:
                field_counts[field]["correct"] += 1

    field_accuracy = {
        field: counts["correct"] / counts["total"] if counts["total"] > 0 else 0
        for field, counts in field_counts.items()
    }

    return {
        "relevance_accuracy": relevance_correct / total,
        "filter_match_accuracy": filter_match / total,
        "field_accuracy": field_accuracy,
        "total_queries": total,
    }
