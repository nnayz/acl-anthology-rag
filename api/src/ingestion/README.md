How to run download.py

Must have uv installed

source .venv/bin/activateActivate environemnt 
go to ingestion folder 
Run python download.py file 
A new folder will be created called data within api/src/ingestion/data/raw 
The raw folder contains the acl_metadata.json file 

# Running `download.py`

This guide explains how to download ACL Anthology metadata using the `download.py` script.

## Prerequisites
- Ensure `uv` is installed.
- Python 3.10+ is recommended.
- Virtual environment is set up for the project.

## Steps

1. **Activate the virtual environment**  
source .venv/bin/activate

2. **Navigate to the ingestion folder**
cd api/src/ingestion

3. **Run Script**
python download.py

## Output: 
A file named data will be automatically created at 
api/src/ingestion/data/raw/acl_metadata.json

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