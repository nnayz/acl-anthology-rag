# Evaluation

This document describes the offline evaluation pipeline under `api/eval/`.

## Overview

The evaluation suite runs a curated set of queries through the **live** retrieval pipeline (`src/retrieval/pipeline.py`), captures:
- retrieved results
- extracted filters
- reformulated queries
- streaming response text
- per-stage timestamps

It then computes metrics and saves a timestamped JSON report.

The pipeline is designed to support two modes:
- `quick`: deterministic metrics only (retrieval + filter parsing + latency)
- `full`: includes LLM-as-judge metrics for generation quality + reformulation quality

## Running Evaluation

From `api/`:

- `python -m eval.scripts.run_eval --suite quick`
- `python -m eval.scripts.run_eval --suite full`
- `python -m eval.scripts.run_eval --suite full --categories simple_factual,filtered`

Results are written to:
- `api/eval/data/results/`
- `api/eval/data/results/latest.json` (convenience pointer)

## Dataset Format

Ground truth is loaded from `api/eval/data/ground_truth.json`.

Each entry is a JSON object (per query) with fields such as:
- `id`: unique identifier
- `category`: category label (e.g., `filtered`, `simple_factual`, `irrelevant`)
- `query`: the user query text
- `expected_is_relevant`: whether the system should treat the query as in-scope
- `expected_filters`: expected structured filters (when applicable)
- `expected_relevant_paper_ids`: set/list of ACL IDs expected to be retrieved

## Metric Suites

### 1) Filter Parsing Metrics (`eval/metrics/filter_parsing.py`)

- **Relevance classification accuracy**: fraction of queries where `is_relevant` matches `expected_is_relevant`.
- **Filter match accuracy**: fraction of relevant queries where all expected filter fields match.
- **Field-level accuracy**: per-field correctness (e.g., `year`, `authors`, `language`).

### 2) Retrieval Metrics (`eval/metrics/retrieval.py`)

Computed by comparing retrieved paper IDs against ground truth relevant paper IDs.

- `precision@k`
- `recall@k`
- `ndcg@k`
- `hit_rate@k`
- `mrr`

### 3) Latency Metrics (`eval/metrics/latency.py`)

Computed from pipeline timestamps emitted in `StreamMetadata.timestamps`:
- `start`
- `filterParsed`
- `queriesReformed`
- `searchCompleted`
- `responseGenerated`

The report includes per-stage latencies and aggregate statistics (mean/median/p95).

### 4) Generation Metrics (LLM-as-judge) (`eval/metrics/generation.py`) (full suite)

Three judge-scored dimensions (0–1):
- **Faithfulness**: response claims are supported by retrieved abstracts
- **Answer relevance**: response addresses the user query
- **Groundedness / citation accuracy**: bracket citations `[N]` match the numbered retrieved papers

### 5) Reformulation Quality (LLM-as-judge) (`eval/metrics/reformulation.py`) (full suite)

Judge-scored dimensions (0–1):
- `fidelity`
- `diversity`
- `specificity`
- `domain_appropriateness`
- `overall`

## Ablations

Ablation experiments are implemented in `api/eval/ablations/runner.py` and can be run via:

- `python -m eval.scripts.run_ablation --experiment all`
- `python -m eval.scripts.run_ablation --experiment reformulation`
- `python -m eval.scripts.run_ablation --experiment rrf`
- `python -m eval.scripts.run_ablation --experiment topk`
- `python -m eval.scripts.run_ablation --experiment filter`

## Reports / Charts

To generate charts and tables from `latest.json`:

- `python -m eval.scripts.generate_report`

This uses `eval/reports/visualizer.py` and (optionally) ablation results to produce plots such as:
- retrieval metrics by category
- latency breakdown
- reformulation ablation curves
- RRF grid heatmap
- irrelevance confusion matrix
