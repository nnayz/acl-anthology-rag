"""
Embedding generation for ACL Anthology abstracts.

This module handles the conversion of preprocessed text into
dense vector embeddings using a sentence transformer model.

The same embedding model must be used for both ingestion and
query-time embedding to ensure vector space consistency.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import uuid

# Add parent directory to path to allow imports when running as script
# This ensures 'src' module can be found when running: python3 src/ingestion/embed.py
script_dir = Path(__file__).resolve().parent
api_dir = script_dir.parent.parent  # Go up from ingestion -> src -> api
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

import gc
import time
import ijson
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct, Filter, FieldCondition, MatchValue
from qdrant_client.http.exceptions import ResponseHandlingException
import httpx

from src.core.config import settings
from src.vectorstore.client import get_qdrant_client


class EmbeddingPipeline:
    """
    Pipeline for embedding documents and loading them into Qdrant vector database.
    
    This class provides a memory-efficient streaming approach to process large
    JSON files containing paper abstracts, generate embeddings, and store them
    in a vector database.
    
    Attributes:
        collection_name: Name of the Qdrant collection to store embeddings
        embedding_dim: Dimension of embeddings produced by the model
        batch_size: Number of documents to process in each batch
        seed: Random seed for reproducible model initialization
        model: Loaded sentence transformer model (lazy-loaded)
        client: Qdrant client instance (lazy-loaded)
    """
    
    def __init__(
        self,
        collection_name: str = "acl-anthology",
        embedding_dim: int = 768,
        batch_size: int = 4,  # Reduced for low-memory systems (8GB RAM)
        seed: int = 42,
        device: Optional[str] = None,
    ):
        """
        Initialize the embedding pipeline.
        
        Args:
            collection_name: Name of the Qdrant collection
            embedding_dim: Expected dimension of embeddings
            batch_size: Number of documents per batch (default: 4 for 8GB RAM systems)
            seed: Random seed for model initialization
            device: Device to use ('cpu' or 'cuda'). If None, auto-detects.
        """
        self.collection_name = collection_name
        self.embedding_dim = embedding_dim
        self.batch_size = batch_size
        self.seed = seed
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        
        # Lazy-loaded components
        self._model: Optional[SentenceTransformer] = None
        self._client: Optional[QdrantClient] = None
    
    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load and return the embedding model."""
        if self._model is None:
            self._model = self._load_model()
        return self._model
    
    @property
    def client(self) -> QdrantClient:
        """Lazy-load and return the Qdrant client with increased timeout."""
        if self._client is None:
            # Use 60 second timeout for large batch uploads
            self._client = get_qdrant_client(timeout=60.0)
        return self._client
    
    def _load_model(self) -> SentenceTransformer:
        """
        Load the sentence transformer model with deterministic seed.
        
        Returns:
            Initialized and configured SentenceTransformer model
        """
        torch.manual_seed(self.seed)
        
        # Force CPU for low-memory systems to avoid GPU memory issues
        device_str = "cpu" if self.device == "cpu" else None
        
        model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            device=device_str,
            trust_remote_code=True  # Required for some models like nomic-ai/nomic-embed-text-v1.5
        )
        model.eval()  # Set to evaluation mode (disables dropout, etc.)
        
        # Clear any cached memory
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        
        return model
    
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
            limit: Maximum number of points to retrieve (for memory efficiency)
            
        Returns:
            Set of paper_ids that already exist in the collection
        """
        existing_ids = set()
        
        try:
            # Use scroll to retrieve all points with their payloads
            # This is memory-efficient as it streams results
            offset = None
            while True:
                result = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=min(limit, 100),  # Process in smaller chunks
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,  # Don't need vectors, just paper_ids
                )
                
                points, next_offset = result
                
                # Extract paper_ids from payloads
                for point in points:
                    if point.payload and "paper_id" in point.payload:
                        existing_ids.add(point.payload["paper_id"])
                
                if next_offset is None:
                    break
                offset = next_offset
                
                # Safety limit to avoid loading too many into memory
                if len(existing_ids) >= limit:
                    print(f"\nWarning: Found {len(existing_ids)} existing papers. "
                          f"Will check remaining papers individually.")
                    break
                    
        except Exception as e:
            print(f"\nWarning: Could not retrieve existing paper IDs: {e}")
            print("Will process all documents (may create duplicates)")
        
        return existing_ids
    
    def _check_paper_exists(self, paper_id: str) -> bool:
        """
        Check if a paper_id already exists in the collection.
        
        Args:
            paper_id: The paper ID to check
            
        Returns:
            True if paper exists, False otherwise
        """
        try:
            # Use scroll with filter to check if paper_id exists
            result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="paper_id",
                            match=MatchValue(value=paper_id)
                        )
                    ]
                ),
                limit=1,
                with_payload=False,
                with_vectors=False,
            )
            points, _ = result
            return len(points) > 0
        except Exception:
            # If filter fails, assume it doesn't exist to be safe
            return False
    
    def _process_batch(self, batch: List[Dict]):
        """
        Process a single batch of documents: embed and upload to Qdrant.
        
        Args:
            batch: List of document dictionaries containing abstracts
        """
        # Extract abstracts from batch for embedding
        texts = [doc["abstract"] for doc in batch]
        
        # Generate embeddings for all texts in the batch
        # normalize_embeddings=True ensures unit vectors for cosine similarity
        # convert_to_numpy=True to avoid keeping tensors in memory
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,  # Disable per-batch progress to avoid clutter
            convert_to_numpy=True,  # Convert to numpy immediately to free GPU memory
            batch_size=len(texts),  # Process all texts in one go (already batched)
        )

        # Verify embedding dimension matches expected size
        assert embeddings.shape[1] == self.embedding_dim

        # Create Qdrant point structures with unique UUIDs
        # Each point contains: unique ID, embedding vector, and original document payload
        points = [
            PointStruct(
                id=str(uuid.uuid4()),  # Generate unique identifier for each document
                vector=vector.tolist(),  # Convert numpy array to list for JSON serialization
                payload=doc,  # Store original paper metadata (paper_id, title, etc.)
            )
            for doc, vector in zip(batch, embeddings)
        ]

        # Upload batch to Qdrant vector database with retry logic
        max_retries = 5  # Increased retries for network issues
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                self.client.upsert(collection_name=self.collection_name, points=points)
                break  # Success, exit retry loop
            except (ResponseHandlingException, httpx.ReadTimeout, httpx.TimeoutException, Exception) as e:
                if attempt == max_retries - 1:
                    # Last attempt failed, raise the exception
                    print(f"\nFailed to upload batch after {max_retries} attempts: {e}")
                    raise
                # Wait before retrying with exponential backoff
                wait_time = retry_delay * (2 ** attempt)
                print(f"\nUpload timeout (attempt {attempt + 1}/{max_retries}), retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        # Explicitly clear memory after processing batch
        del texts, embeddings, points
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    def run(self, file_path: Path, resume: bool = True) -> int:
        """
        Stream documents from JSON file, embed abstracts in batches, and upload to Qdrant.
        
        Uses streaming JSON parsing to process large files without loading everything
        into memory. Only keeps one batch of documents in memory at a time.
        
        Args:
            file_path: Path to the processed JSON file containing paper documents
            resume: If True, skip documents that are already embedded (default: True)
            
        Returns:
            Total number of documents processed and embedded
            
        Raises:
            FileNotFoundError: If the specified file does not exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Processed file not found: {file_path}")
        
        # Initialize components
        self.ensure_collection()
        
        # Load existing paper IDs if resuming
        existing_paper_ids = set()
        if resume:
            print("Checking for existing papers in collection...")
            existing_paper_ids = self._get_existing_paper_ids(limit=50000)
            print(f"Found {len(existing_paper_ids)} papers already embedded. "
                  f"Will skip these and continue with remaining papers.")
        
        batch = []
        total_processed = 0
        total_skipped = 0

        # Open file in binary mode for ijson streaming parser
        # ijson streams JSON parsing without loading entire file into memory
        with file_path.open("rb") as f:
            # Parse JSON array: "item" refers to each element in the root array
            parser = ijson.items(f, "item")
            
            # Stream documents one at a time and accumulate into batches
            for doc in tqdm(parser, desc="Embedding ACL abstracts"):
                paper_id = doc.get("paper_id")
                
                # Skip if already embedded (when resuming)
                if resume and paper_id and paper_id in existing_paper_ids:
                    total_skipped += 1
                    continue
                
                # If paper_id not in our set, double-check individually (for papers beyond limit)
                if resume and paper_id and len(existing_paper_ids) >= 50000:
                    if self._check_paper_exists(paper_id):
                        total_skipped += 1
                        continue
                
                batch.append(doc)
                
                # Process batch when it reaches the target size
                # This keeps memory usage constant regardless of file size
                if len(batch) >= self.batch_size:
                    try:
                        self._process_batch(batch)
                        total_processed += len(batch)
                        batch = []  # Clear batch to free memory
                        # Force garbage collection after each batch for low-memory systems
                        gc.collect()
                        # Small delay to avoid overwhelming the API
                        time.sleep(0.1)
                    except Exception as e:
                        # Log error but continue processing
                        print(f"\nError processing batch at document {total_processed}: {e}")
                        print(f"Continuing with next batch...")
                        batch = []  # Clear failed batch
                        gc.collect()
                        # Wait a bit longer after error
                        time.sleep(2)
            
            # Process remaining documents in the last batch (if file size not divisible by batch_size)
            if batch:
                try:
                    self._process_batch(batch)
                    total_processed += len(batch)
                except Exception as e:
                    print(f"\nError processing final batch: {e}")
        
        if resume and total_skipped > 0:
            print(f"\nSkipped {total_skipped} papers that were already embedded.")
        
        return total_processed
    
    @staticmethod
    def get_latest_processed_file(processed_dir: Optional[Path] = None) -> Path:
        """
        Return the most recent processed JSON file in the data/processed folder.
        
        Args:
            processed_dir: Optional custom directory path. If None, uses default location.
            
        Returns:
            Path to the most recently modified JSON file
            
        Raises:
            FileNotFoundError: If no processed JSON files are found
        """
        if processed_dir is None:
            # Locate processed directory: go up from ingestion -> src -> api, then to data/processed
            # Path(__file__) = api/src/ingestion/embed.py
            # .parent = api/src/ingestion/
            # .parent.parent = api/src/
            # .parent.parent.parent = api/
            script_dir = Path(__file__).resolve().parent
            api_dir = script_dir.parent.parent.parent  # Go up from ingestion -> src -> api
            processed_dir = api_dir / "api" / "data" / "processed"
        
        json_files = list(processed_dir.glob("*.json"))
        if not json_files:
            raise FileNotFoundError(f"No processed JSON files found in {processed_dir}")
        
        # Select file with most recent modification time (latest preprocessing run)
        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        return latest_file


def main():
    """Main entry point for running the embedding pipeline."""
    # Use smaller batch size and CPU for low-memory systems (8GB RAM)
    pipeline = EmbeddingPipeline(
        batch_size=4,  # Small batch size for 8GB RAM systems
        device="cpu"   # Force CPU to avoid GPU memory issues
    )
    processed_file = EmbeddingPipeline.get_latest_processed_file()
    print(f"Using processed file: {processed_file}")
    print(f"Batch size: {pipeline.batch_size}, Device: {pipeline.device}")
    
    # Resume mode: skip papers that are already embedded
    total_processed = pipeline.run(processed_file, resume=True)
    print(f"Successfully processed and embedded {total_processed} new documents")


if __name__ == "__main__":
    main()
