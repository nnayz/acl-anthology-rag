"""Ground truth dataset loading and management."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from eval.config import eval_config

logger = logging.getLogger(__name__)


class GroundTruthDataset:
    """Manages the ground truth evaluation dataset."""

    def __init__(self, path: Optional[str] = None):
        self.path = Path(path or eval_config.GROUND_TRUTH_PATH)
        self._data: Optional[Dict[str, Any]] = None
        self._queries: Optional[List[Dict[str, Any]]] = None

    def load(self) -> "GroundTruthDataset":
        """Load the ground truth dataset from JSON."""
        if not self.path.exists():
            raise FileNotFoundError(f"Ground truth file not found: {self.path}")

        with open(self.path, "r") as f:
            self._data = json.load(f)

        self._queries = self._data.get("queries", [])
        logger.info(
            f"Loaded {len(self._queries)} ground truth queries from {self.path}"
        )
        return self

    @property
    def queries(self) -> List[Dict[str, Any]]:
        if self._queries is None:
            self.load()
        return self._queries  # type: ignore[return-value]

    def get_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get queries filtered by category."""
        return [q for q in self.queries if q.get("category") == category]

    def get_by_categories(self, categories: List[str]) -> List[Dict[str, Any]]:
        """Get queries filtered by multiple categories."""
        cat_set = set(categories)
        return [q for q in self.queries if q.get("category") in cat_set]

    @property
    def categories(self) -> List[str]:
        """Get all unique categories."""
        return sorted(set(q.get("category", "unknown") for q in self.queries))

    def __len__(self) -> int:
        return len(self.queries)

    def __iter__(self):
        return iter(self.queries)


def load_ground_truth(path: Optional[str] = None) -> GroundTruthDataset:
    """Load and return the ground truth dataset."""
    return GroundTruthDataset(path).load()
