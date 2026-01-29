"""
Vercel entrypoint for FastAPI application.

This module creates a FastAPI app directly for Vercel deployment,
avoiding import path issues with the nested src structure.
"""

import logging
import sys
from pathlib import Path

# Add the api directory to the path so imports work correctly
sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

app = FastAPI(
    title="ACL Anthology RAG API",
    description="API for semantic retrieval over ACL Anthology papers",
    version="0.1.0",
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for Vercel deployment
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(router)


@app.get("/ping")
async def ping():
    """Health check endpoint."""
    return {"message": "pong"}
