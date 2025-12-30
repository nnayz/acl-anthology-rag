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