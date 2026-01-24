# System Architecture

This document provides a detailed breakdown of the ACL Anthology RAG system architecture, including its major components, design patterns, and data flow.

## High-Level Overview

The system is designed as a modular Retrieval-Augmented Generation (RAG) pipeline. It decouples the offline ingestion of data from the online retrieval of information, allowing for scalable and efficient searching.

```mermaid
graph TD
    subgraph "Frontend"
        UI[React UI]
    end

    subgraph "Backend API"
        API[FastAPI Router]
        QP[Query Processor]
        Agg[Result Aggregator]
    end

    subgraph "Core Logic"
        Ref[LLM Reformulator]
        Emb[Embedding Service]
        Ret[Retrieval Pipeline]
    end

    subgraph "Data Storage"
        Qdrant[Qdrant Vector DB]
        Raw[Raw ACL Data]
    end

    UI <--> API
    API --> QP
    QP --> Ref
    Ref --> Emb
    Emb --> Ret
    Ret <--> Qdrant
    Ret --> Agg
    Agg --> API
```

## Component Breakdown

### 1. Frontend Client
- **Tech Stack:** React 19, Vite, TailwindCSS, shadcn/ui.
- **Responsibilities:**
  - Accepts user input (Natural Language or Paper ID).
  - Displays retrieved papers with metadata (Title, Abstract, Year, Authors).
  - Visualizes the search process (loading states, query expansion results).
- **Key Components:**
  - `SearchInterface`: Main input component handling mode switching.
  - `ResultCard`: Displays individual paper details.

### 2. Backend API
- **Tech Stack:** FastAPI, Python 3.12.
- **Responsibilities:**
  - Exposes REST endpoints for search.
  - Handles request validation and error management.
  - Orchestrates the retrieval pipeline.
- **Key Modules:**
  - `api/src/app.py`: Application entry point and middleware configuration.
  - `api/src/api/routes.py`: Defines endpoints like `/search`.

### 3. Query Processor (`api/src/retrieval/query_processor.py`)
- **Role:** Interprets the raw user input.
- **Logic:**
  - If input is a **Paper ID** (e.g., `2023.acl-long.1`), it fetches the paper's abstract from the raw dataset or API.
  - If input is **Natural Language**, it passes it directly to the next stage.
- **Design Pattern:** Strategy Pattern (handles different input types uniformly).

### 4. LLM Reformulator (`api/src/llm/reformulator.py`)
- **Role:** Expands the initial query into multiple semantic search vectors.
- **Logic:**
  - Uses an LLM (Groq or Fireworks) to generate synonyms, related concepts, and paraphrases.
  - Improves recall by covering a wider area of the vector space.
- **Configuration:** Adjustable number of generated queries (default: 3).

### 5. Embedding Service (`api/src/ingestion/embed.py`)
- **Role:** Converts text into dense vectors.
- **Model:** Defaults to `nomic-ai/nomic-embed-text-v1.5` (768 dimensions).
- **Usage:**
  - **Offline:** Embeds all paper abstracts.
  - **Online:** Embeds the reformulated search queries.

### 6. Retrieval Pipeline (`api/src/retrieval/pipeline.py`)
- **Role:** Executes the search against the vector database.
- **Logic:**
  - Performs nearest neighbor search for *each* of the reformulated queries.
  - Retrieves `k` candidates for each query.

### 7. Result Aggregator (`api/src/retrieval/aggregator.py`)
- **Role:** Merges results from multiple queries into a single ranked list.
- **Algorithm:** Reciprocal Rank Fusion (RRF).
- **Logic:**
  - Assigns scores based on the rank of a paper in each result set.
  - Favors papers that appear in multiple result sets or rank highly in single sets.
  - Deduplicates papers.

### 8. Vector Database
- **Tech Stack:** Qdrant (Dockerized).
- **Role:** Stores abstract embeddings and metadata (Title, URL, Year).
- **Schema:**
  - `vector`: 768-dim float array.
  - `payload`: JSON object with paper metadata.

## Design Patterns

### Retrieval-Augmented Generation (RAG)
While typically used for generating answers, here the "Generation" part is primarily used for **Query Expansion**, and the final output is the retrieved documents themselves. This is often called **RAG for Retrieval**.

### Reciprocal Rank Fusion (RRF)
Used to combine results from the multiple generated queries without needing complex re-ranking models. It provides a robust way to fuse rankings.

### Separation of Concerns
- **Ingestion** is strictly offline.
- **Retrieval** is strictly read-only online.
- **Shared Components** (like Embedding) are reused to ensure consistency between indexing and querying.

## Data Flow

### Offline Ingestion Flow
1. **Download**: `acl-anthology` library fetches metadata.
2. **Clean**: Text is normalized (unicode normalization, whitespace stripping).
3. **Embed**: Batches of abstracts are sent to the embedding model.
4. **Upsert**: Vectors + Payload are pushed to Qdrant.

### Online Search Flow
1. **Input**: User provides "Machine Translation".
2. **Reformulate**: LLM generates:
   - "Neural Machine Translation state of the art"
   - "Low-resource language translation"
   - "Transformer based translation models"
3. **Embed**: All 3 strings are embedded.
4. **Search**: Qdrant runs 3 separate searches.
5. **Fuse**: RRF combines the 3 lists of papers.
6. **Return**: Top 30 unique papers returned to UI.

## Extension Points

- **New Embedding Models**: Change `EMBEDDING_MODEL` in config.
- **Different LLMs**: Switch providers in `api/src/llm/`.
- **Hybrid Search**: Add keyword-based search (BM25) to Qdrant and fuse with dense vectors.
