"""
FastAPI application definition.

This module creates and configures the FastAPI application instance,
including middleware, exception handlers, and router registration.
"""

from fastapi import FastAPI

app = FastAPI(
    title="ACL Anthology RAG API",
    description="API for semantic retrieval over ACL Anthology papers",
    version="0.1.0",
)


@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"message": "pong"}

