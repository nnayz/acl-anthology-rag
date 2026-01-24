"""
Vercel entrypoint for FastAPI application.

This module re-exports the FastAPI app instance for Vercel deployment.
"""

from src.api.app import app

__all__ = ["app"]
