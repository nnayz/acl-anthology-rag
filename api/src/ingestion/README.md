# Ingestion Pipeline

This directory contains the offline ingestion scripts that build the ACL Anthology dataset used for retrieval.

The pipeline stages are:
1. `download.py`: fetch metadata + abstracts from the ACL Anthology
2. `preprocess.py`: clean and normalize the downloaded dataset
3. `embed.py`: generate embeddings and (optionally) write intermediate artifacts

You typically run these from the repo root or from `api/` using `uv`.

## Prerequisites
- Ensure `uv` is installed.
- Python 3.12+ (matches the backend).
- A configured `api/.env` with `FIREWORKS_API_KEY` (embeddings) and Qdrant connection details.

## Steps

1. **Activate the virtual environment**  
source .venv/bin/activate

2. **Navigate to the ingestion folder**
cd api/src/ingestion

3. **Run Script**
python download.py

## Output
The raw metadata is written under:
`api/src/ingestion/data/raw/acl_metadata.json`

# Running `preprocess.py` (Issue 1.2: Clean and normalize abstracts)

This script cleans and normalizes the downloaded metadata for downstream embedding.

## What it does

- **Remove formatting artifacts**: normalizes text using Unicode NFKC.
- **Normalize whitespace**: replaces newlines/tabs with spaces and collapses repeated whitespace.
- **Handle missing or empty abstracts**: papers with missing/empty abstracts are skipped.
- **Log dropped/skipped papers**: skipped papers are logged with their `paper_id`.

## Input

- Raw metadata JSON produced by `download.py`.

`preprocess.py` will look for the raw file in either of these locations:

- `api/src/ingestion/data/raw/acl_metadata.json`
- `data/raw/acl_metadata.json`

## Output

- **Processed (cleaned) dataset** is written under the corresponding processed folder:

  - `api/src/ingestion/data/processed/acl_cleaned_<UTC_TIMESTAMP>.json`
  - or `data/processed/acl_cleaned_<UTC_TIMESTAMP>.json`

The output is **versioned** via a UTC timestamp suffix to avoid overwriting previous runs.

## Run

From the repo root:

- `python3 api/src/ingestion/preprocess.py`

## Recommended full run (from `api/`)

- `uv run python src/ingestion/download.py`
- `uv run python src/ingestion/preprocess.py`
- `uv run python src/ingestion/embed.py`