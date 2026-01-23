"""
FastAPI application definition.

This module creates and configures the FastAPI application instance,
including middleware, exception handlers, and router registration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

app = FastAPI(
    title="ACL Anthology RAG API",
    description="API for semantic retrieval over ACL Anthology papers",
    version="0.1.0",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,  # ty:ignore[invalid-argument-type]
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(router)


@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"message": "pong"}
