"""
ACL Anthology data downloader.

This module is responsible for fetching paper abstracts and metadata
from the ACL Anthology. It handles API requests, rate limiting, and
data extraction.

Primary responsibilities:
- Fetch individual papers by ACL ID
- Bulk download papers from specific venues/years
- Parse and extract metadata from ACL Anthology responses

Fetches ACL Anthology metadata using the official Python package
and stores it as a JSON file in data/raw/acl_metadata.json.

This version automatically fetches the repo using Anthology.from_repo()

Requirements: Pip install acl-anthology / uv add acl-anthology
"""

from acl_anthology import Anthology
import json
import os

def main():
    print("Fetching ACL Anthology data...")
    anthology = Anthology.from_repo()  # Automatically fetch repo

    # Determine correct output directory
    base_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.abspath(os.path.join(base_dir, "..", ".."))
    
    # Use api/data/raw as the output directory
    RAW_DATA_DIR = os.path.join(api_dir, "data", "raw")
    os.makedirs(RAW_DATA_DIR, exist_ok=True)
    OUTPUT_FILE = os.path.join(RAW_DATA_DIR, "acl_metadata.json")

    records = []
    total = 0

    for paper in anthology.papers():
        total += 1

        # Convert MarkupText fields to strings
        title = str(paper.title) if paper.title else None
        abstract = str(paper.abstract) if paper.abstract else None

        # Year directly available
        year = paper.year

        # Event(s)
        events = paper.get_events()
        event_ids = [event.id for event in events] if events else []

        # Bibkey, DOI, language
        bibkey = paper.bibkey
        doi = paper.doi
        language = paper.language

        # Authors
        authors = [f"{a.name.first} {a.name.last}".strip() for a in paper.authors] if paper.authors else []

        # Awards
        awards = paper.awards if paper.awards else []

        # PDF URL
        pdf_url = paper.pdf.url if paper.pdf else None

        record = {
            "paper_id": paper.full_id,
            "title": title,
            "abstract": abstract,
            "year": year,
            "event": event_ids,  # can be a list if multiple events
            "bibkey": bibkey,
            "doi": doi,
            "language": language,
            "authors": authors,
            "awards": awards,
            "pdf_url": pdf_url
        }
        records.append(record)

        # Optional: print progress every 5000 papers
        if total % 5000 == 0:
            print(f"Processed {total} papers...")

    # Save JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    print(f"\nSaved {len(records)} papers to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
