"""
Text preprocessing for ACL Anthology abstracts.

This module handles cleaning and normalization of abstract text
before embedding generation. Preprocessing steps include:
- Unicode normalization
- Whitespace cleanup
- Special character handling
- Citation marker removal (optional)
"""

import json
import os
import logging
import re
import unicodedata
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


def clean_text(text: Optional[str]) -> str:
    """
    Normalize whitespace and remove formatting artifacts from text.

    Args:
        text: Input text string

    Returns:
        Cleaned text string
    """
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[\n\t\r]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def process_data():
    """
    Load raw data, clean it, and save to processed directory.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(base_dir, "..", "..", ".."))
    api_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))

    candidate_raw_paths = [
        os.path.join(
            api_dir, "data", "raw", "acl_metadata.json"
        ),  # api/data/raw/acl_metadata.json
        os.path.join(
            base_dir, "data", "raw", "acl_metadata.json"
        ),  # api/src/ingestion/data/raw/acl_metadata.json
        os.path.join(
            repo_root, "data", "raw", "acl_metadata.json"
        ),  # data/raw/acl_metadata.json (project root)
    ]
    raw_data_path = next((p for p in candidate_raw_paths if os.path.exists(p)), None)

    if raw_data_path is None:
        logger.error(
            "Raw data file not found. Looked in: " + ", ".join(candidate_raw_paths)
        )
        return

    raw_data_dir = os.path.dirname(raw_data_path)
    processed_dir = os.path.join(os.path.dirname(raw_data_dir), "processed")
    version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_file = os.path.join(processed_dir, f"acl_cleaned_{version}.json")

    # Ensure processed directory exists
    os.makedirs(processed_dir, exist_ok=True)

    logger.info(f"Loading raw data from {raw_data_path}")

    try:
        with open(raw_data_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON: {e}")
        return
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return

    processed_data: List[Dict] = []
    stats = {
        "total": 0,
        "kept": 0,
        "skipped_no_abstract": 0,
        "skipped_empty_abstract": 0,
    }

    logger.info("Starting data processing...")

    for paper in raw_data:
        stats["total"] += 1

        paper_id = paper.get("paper_id", "unknown")
        raw_abstract = paper.get("abstract")

        # specific check for None or non-string
        if not raw_abstract or not isinstance(raw_abstract, str):
            logger.warning(f"Skipping paper {paper_id}: Missing abstract")
            stats["skipped_no_abstract"] += 1
            continue

        cleaned_abstract = clean_text(raw_abstract)

        if not cleaned_abstract:
            logger.warning(f"Skipping paper {paper_id}: Empty abstract after cleaning")
            stats["skipped_empty_abstract"] += 1
            continue

        # Clean title as well
        paper["title"] = clean_text(paper.get("title", ""))
        paper["abstract"] = cleaned_abstract

        processed_data.append(paper)
        stats["kept"] += 1

    # Save processed data
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved {len(processed_data)} processed papers to {output_file}")
        logger.info(f"Processing stats: {json.dumps(stats, indent=2)}")
    except Exception as e:
        logger.error(f"Failed to save processed data: {e}")


if __name__ == "__main__":
    process_data()
