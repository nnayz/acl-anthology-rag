"""
Embedding generation for ACL Anthology abstracts.

This module handles the conversion of preprocessed text into
dense vector embeddings using LangChain's embedding abstractions.

Uses the centralized LangChain component management from
src.vectorstore.client for consistent embedding model usage
across ingestion and retrieval.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import uuid

# Add parent directory to path to allow imports when running as script
script_dir = Path(__file__).resolve().parent
api_dir = script_dir.parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

import gc
import time
import ijson
from tqdm import tqdm
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client.models import VectorParams, Distance
from qdrant_client.http.exceptions import ResponseHandlingException
import httpx

from src.core.config import settings
from src.vectorstore.client import LangChainComponents, get_langchain_components


class EmbeddingPipeline:
    """
    Pipeline for embedding documents and loading them into Qdrant vector database.

    Uses centralized LangChain components for consistent embedding generation
    across ingestion and retrieval.

    Attributes:
        collection_name: Name of the Qdrant collection to store embeddings
        embedding_dim: Dimension of embeddings produced by the model
        batch_size: Number of documents to process in each batch
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedding_dim: Optional[int] = None,
        batch_size: Optional[int] = None,
        device: Optional[str] = None,
    ):
        """
        Initialize the embedding pipeline.

        Args:
            collection_name: Name of the Qdrant collection (default: from settings)
            embedding_dim: Expected dimension of embeddings (default: from settings)
            batch_size: Number of documents per batch (default: from settings)
            device: Device to use ('cpu' or 'cuda'). If None, defaults to 'cpu'.
        """
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.embedding_dim = embedding_dim or settings.EMBEDDING_DIM
        self.batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        self.device = device or "cpu"

        # Use centralized LangChain components
        self._components: Optional[LangChainComponents] = None
        self._vectorstore: Optional[QdrantVectorStore] = None

    @property
    def components(self) -> LangChainComponents:
        """Get configured LangChain components."""
        if self._components is None:
            self._components = get_langchain_components().configure(device=self.device)
        return self._components

    @property
    def embeddings(self):
        """Get the LangChain embedding model from centralized components."""
        return self.components.embeddings

    @property
    def client(self):
        """Get the Qdrant client from centralized components."""
        return self.components.qdrant_client

    @property
    def vectorstore(self) -> QdrantVectorStore:
        """Get or create the vector store for the collection."""
        if self._vectorstore is None:
            self.ensure_collection()
            self._vectorstore = QdrantVectorStore(
                client=self.client,
                collection_name=self.collection_name,
                embedding=self.embeddings,
            )
        return self._vectorstore

    def ensure_collection(self):
        """Create the Qdrant collection if it does not exist."""
        if not self.client.collection_exists(self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.embedding_dim,
                    distance=Distance.COSINE,
                ),
            )

    def _get_existing_paper_ids(self, limit: int = 10000) -> set:
        """
        Get set of paper_ids that are already in the collection.

        Args:
            limit: Maximum number of points to retrieve

        Returns:
            Set of paper_ids that already exist in the collection
        """
        existing_ids = set()

        try:
            offset = None
            while True:
                result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=min(limit, 100),
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                points, next_offset = result

                for point in points:
                    if point.payload and "paper_id" in point.payload:
                        existing_ids.add(point.payload["paper_id"])

                if next_offset is None:
                    break
                offset = next_offset

                if len(existing_ids) >= limit:
                    print(f"\nWarning: Found {len(existing_ids)} existing papers.")
                    break

        except Exception as e:
            print(f"\nWarning: Could not retrieve existing paper IDs: {e}")

        return existing_ids

    def _process_batch_with_langchain(self, batch: List[Dict]):
        """
        Process a batch using LangChain's vector store.

        Args:
            batch: List of document dictionaries
        """
        # Convert to LangChain Documents
        documents = [
            Document(
                page_content=doc["abstract"],
                metadata={
                    "paper_id": doc.get("paper_id", ""),
                    "title": doc.get("title", ""),
                    "abstract": doc.get("abstract", ""),
                    "year": doc.get("year"),
                    "authors": doc.get("authors"),
                    "pdf_url": doc.get("pdf_url"),
                },
            )
            for doc in batch
        ]

        # Generate unique IDs
        ids = [str(uuid.uuid4()) for _ in documents]

        # Use LangChain's add_documents with retry logic
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.vectorstore.add_documents(documents, ids=ids)
                break
            except (
                ResponseHandlingException,
                httpx.ReadTimeout,
                httpx.TimeoutException,
                Exception,
            ) as e:
                if attempt == max_retries - 1:
                    print(f"\nFailed to upload batch after {max_retries} attempts: {e}")
                    raise
                wait_time = retry_delay * (2**attempt)
                print(
                    f"\nUpload timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s..."
                )
                time.sleep(wait_time)

        # Clear memory
        del documents, ids
        gc.collect()

    def run(self, file_path: Path, resume: bool = True) -> int:
        """
        Stream documents from JSON file, embed abstracts, and upload to Qdrant.

        Args:
            file_path: Path to the processed JSON file
            resume: If True, skip documents that are already embedded

        Returns:
            Total number of documents processed
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Processed file not found: {file_path}")

        self.ensure_collection()

        existing_paper_ids = set()
        if resume:
            print("Checking for existing papers in collection...")
            existing_paper_ids = self._get_existing_paper_ids(limit=50000)
            print(f"Found {len(existing_paper_ids)} papers already embedded.")

        batch = []
        total_processed = 0
        total_skipped = 0

        with file_path.open("rb") as f:
            parser = ijson.items(f, "item")

            for doc in tqdm(parser, desc="Embedding ACL abstracts"):
                paper_id = doc.get("paper_id")

                if resume and paper_id and paper_id in existing_paper_ids:
                    total_skipped += 1
                    continue

                batch.append(doc)

                if len(batch) >= self.batch_size:
                    try:
                        self._process_batch_with_langchain(batch)
                        total_processed += len(batch)
                        batch = []
                        gc.collect()
                        time.sleep(0.1)
                    except Exception as e:
                        print(f"\nError processing batch: {e}")
                        batch = []
                        gc.collect()
                        time.sleep(2)

            if batch:
                try:
                    self._process_batch_with_langchain(batch)
                    total_processed += len(batch)
                except Exception as e:
                    print(f"\nError processing final batch: {e}")

        if resume and total_skipped > 0:
            print(f"\nSkipped {total_skipped} papers that were already embedded.")

        return total_processed

    @staticmethod
    def get_latest_processed_file(processed_dir: Optional[Path] = None) -> Path:
        """
        Return the most recent processed JSON file.

        Args:
            processed_dir: Optional custom directory path.

        Returns:
            Path to the most recently modified JSON file
        """
        if processed_dir is None:
            script_dir = Path(__file__).resolve().parent
            api_dir = script_dir.parent.parent.parent
            processed_dir = api_dir / "api" / "data" / "processed"

        json_files = list(processed_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No processed JSON files found in {processed_dir}")

        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        return latest_file


def main():
    """Main entry point for running the embedding pipeline."""
    pipeline = EmbeddingPipeline(batch_size=4, device="cpu")
    processed_file = EmbeddingPipeline.get_latest_processed_file()
    print(f"Using processed file: {processed_file}")
    print(f"Batch size: {pipeline.batch_size}, Device: {pipeline.device}")

    total_processed = pipeline.run(processed_file, resume=True)
    print(f"Successfully processed and embedded {total_processed} new documents")


if __name__ == "__main__":
    main()
