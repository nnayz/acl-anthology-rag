"""Evaluation pipeline configuration."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base directory for evaluation module
EVAL_DIR = Path(__file__).parent
DATA_DIR = EVAL_DIR / "data"
RESULTS_DIR = DATA_DIR / "results"
GROUND_TRUTH_PATH = DATA_DIR / "ground_truth.json"


class EvalConfig:
    """Configuration for the evaluation pipeline."""

    # Judge Model (separate from the pipeline's 8B model)
    JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "llama-3.3-70b-versatile")
    JUDGE_TEMPERATURE = 0.0
    JUDGE_MAX_TOKENS = 1024

    # Groq API (reuses existing key)
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    # Evaluation parameters
    DEFAULT_TOP_K = 5
    RETRIEVAL_K_VALUES = [1, 3, 5, 10]

    # Scoring thresholds
    RELEVANCE_THRESHOLD = 0.5
    FAITHFULNESS_THRESHOLD = 0.7

    # Ablation parameters
    REFORMULATION_COUNTS = [0, 1, 2, 3, 4]
    RRF_K_VALUES = [10, 30, 60, 100]
    RRF_SCORE_WEIGHTS = [0.0, 0.15, 0.3, 0.5, 0.7, 1.0]
    TOP_K_VALUES = [1, 3, 5, 10, 15, 20]

    # Paths
    GROUND_TRUTH_PATH = str(GROUND_TRUTH_PATH)
    RESULTS_DIR = str(RESULTS_DIR)

    # Rate limiting for Groq free tier
    JUDGE_DELAY_SECONDS = 2.0  # delay between judge calls to avoid rate limits


eval_config = EvalConfig()
