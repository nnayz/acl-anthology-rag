"""
Embedding generation for ACL Anthology abstracts.

This module handles the conversion of preprocessed text into
dense vector embeddings using a sentence transformer model.

The same embedding model must be used for both ingestion and
query-time embedding to ensure vector space consistency.
"""

import json
from pathlib import Path
from typing import List, Dict
import uuid

import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from qdrant_client.models import VectorParams, Distance, PointStruct

# Plain Python config (no Pydantic)
from src.core.config import settings
from src.vectorstore.client import get_qdrant_client

# ---------------------------
# Configuration
# ---------------------------

COLLECTION_NAME = "acl-anthology"
EMBEDDING_DIM = 768
BATCH_SIZE = 16
SEED = 42

# ---------------------------
# Load processed documents
# ---------------------------

def load_documents(path: Path) -> List[Dict]:
    """Load preprocessed JSON documents."""
    if not path.exists():
        raise FileNotFoundError(f"Processed file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# ---------------------------
# Initialize embedding model
# ---------------------------

def load_model() -> SentenceTransformer:
    """Load the sentence transformer model with deterministic seed."""
    torch.manual_seed(SEED)
    model = SentenceTransformer(
        settings.EMBEDDING_MODEL,
        trust_remote_code=True  # required for nomic-ai/nomic-embed-text-v1.5
    )
    model.eval()
    return model

# ---------------------------
# Ensure Qdrant collection exists
# ---------------------------

def ensure_collection():
    """Create the Qdrant collection if it does not exist."""
    client = get_qdrant_client()
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIM,
                distance=Distance.COSINE,
            ),
        )

# ---------------------------
# Embed + upload
# ---------------------------

def embed_and_upload(docs: List[Dict]):
    """Embed abstracts in batches and upload to Qdrant using UUIDs as point IDs."""
    model = load_model()
    client = get_qdrant_client()
    ensure_collection()

    for i in tqdm(range(0, len(docs), BATCH_SIZE), desc="Embedding ACL abstracts"):
        batch = docs[i: i + BATCH_SIZE]

        texts = [doc["abstract"] for doc in batch]
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        # sanity check
        assert embeddings.shape[1] == EMBEDDING_DIM

        points = [
            PointStruct(
                id=str(uuid.uuid4()),  # Generate a unique UUID for Qdrant
                vector=vector.tolist(),
                payload=doc,  # Keep original paper_id inside payload
            )
            for doc, vector in zip(batch, embeddings)
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=points)

# ---------------------------
# Entrypoint
# ---------------------------

def get_latest_processed_file() -> Path:
    """Return the most recent processed JSON file in the data/processed folder."""
    processed_dir = Path(__file__).parent / "data/processed"
    json_files = list(processed_dir.glob("*.json"))
    if not json_files:
        raise FileNotFoundError(f"No processed JSON files found in {processed_dir}")
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    return latest_file

def main():
    processed_file = get_latest_processed_file()
    print(f"Using processed file: {processed_file}")
    docs = load_documents(processed_file)
    embed_and_upload(docs)

if __name__ == "__main__":
    main()
    