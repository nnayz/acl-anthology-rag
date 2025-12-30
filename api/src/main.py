"""
Application entry point.

This module serves as the main entry point for running the
ACL Anthology RAG API server using uvicorn.
"""

from uvicorn import run

if __name__ == "__main__":
    run("api.app:app", host="localhost", port=8000, reload=True)
