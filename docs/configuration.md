# Configuration Guide

The ACL Anthology RAG system is configured via environment variables. These are typically stored in a `.env` file in the `api/` directory.

## Core Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `GROQ_API_KEY` | API key for Groq (LLM provider) | - | Yes* |
| `FIREWORKS_API_KEY` | API key for Fireworks AI (Alternative LLM) | - | No |
| `QDRANT_API_KEY` | API key for Qdrant (if using cloud) | - | No |
| `QDRANT_ENDPOINT` | URL for Qdrant instance | `http://localhost:6333` | No |

*\*At least one LLM provider key is required.*

## LLM Configuration

Settings that control the behavior of the Large Language Model used for query reformulation.

| Variable | Description | Default |
|----------|-------------|---------|
| `GROQ_MODEL` | Model ID to use on Groq | `llama-3.1-8b-instant` |
| `LLM_TEMPERATURE` | Creativity of the model (0.0 - 1.0) | `0.3` |
| `LLM_MAX_TOKENS` | Max output tokens for reformulation | `512` |
| `NUM_REFORMULATED_QUERIES` | Number of search queries to generate | `3` |

## Embedding & Vector DB

Settings for the vector representation and storage.

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_MODEL` | HuggingFace model ID for embeddings | `nomic-ai/nomic-embed-text-v1.5` |
| `EMBEDDING_DIM` | Dimension of the embedding vectors | `768` |
| `QDRANT_COLLECTION` | Name of the collection in Qdrant | `acl-anthology` |
| `QDRANT_TIMEOUT` | Request timeout in seconds | `60` |

## Retrieval & Ranking

Parameters tuning the search quality and aggregation.

| Variable | Description | Default |
|----------|-------------|---------|
| `SEARCH_K_MULTIPLIER` | Multiplier for retrieval candidates (k * m) | `2` |
| `RRF_K` | Constant for Reciprocal Rank Fusion | `60` |
| `RRF_SCORE_WEIGHT` | Weight balance for fusion scoring | `0.3` |

## Ingestion Performance

Settings for the offline data processing pipeline.

| Variable | Description | Default |
|----------|-------------|---------|
| `EMBEDDING_BATCH_SIZE` | Number of abstracts to embed at once | `4` |

## Example .env File

```ini
# API Keys
GROQ_API_KEY=gsk_...
# FIREWORKS_API_KEY=fw_...

# Qdrant (Local)
QDRANT_ENDPOINT=http://localhost:6333

# Model Selection
GROQ_MODEL=llama-3.1-70b-versatile
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5

# Tuning
NUM_REFORMULATED_QUERIES=5
LLM_TEMPERATURE=0.2
```
