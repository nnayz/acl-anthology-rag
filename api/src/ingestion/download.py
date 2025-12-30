"""
ACL Anthology data downloader.

This module is responsible for fetching paper abstracts and metadata
from the ACL Anthology. It handles API requests, rate limiting, and
data extraction.

Primary responsibilities:
- Fetch individual papers by ACL ID
- Bulk download papers from specific venues/years
- Parse and extract metadata from ACL Anthology responses
"""
