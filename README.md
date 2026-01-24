# ACL Anthology Semantic Retrieval System

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Version](https://img.shields.io/badge/version-0.1.0-orange)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![React](https://img.shields.io/badge/react-19-blue)

## Motivation

The ACL Anthology hosts tens of thousands of NLP research papers. Traditional keyword-based search often fails to capture the semantic nuance of research queries, struggling with synonyms, paraphrases, and conceptual similarity. 

**ACL Anthology RAG** bridges this gap by implementing a semantic retrieval system. It moves beyond simple keyword matching to understand the *meaning* behind a query, allowing researchers to discover relevant work even when they don't know the exact terminology.

## Key Features

- **Semantic Search**: Uses dense vector embeddings to find conceptually similar papers.
- **Query Reformulation**: Leverages LLMs to expand user queries into multiple search vectors, improving recall.
- **Dual Query Modes**: Supports both natural language questions and "Paper as Query" (using a paper ID to find related work).
- **Unified Pipeline**: A consistent architecture for handling different types of inputs.
- **Modern Stack**: Built with FastAPI, LangChain, Qdrant, and React.

## Architecture Overview

The system follows a Retrieval-Augmented Generation (RAG) pattern, though currently focused on the retrieval aspect.

```mermaid
graph TD
    User[User] -->|Query/Paper ID| Client[React Client]
    Client -->|API Request| API[FastAPI Backend]
    
    subgraph "Online Retrieval"
        API -->|Interpret| QP[Query Processor]
        QP -->|Reformulate| LLM[LLM (Groq/Fireworks)]
        LLM -->|Search Queries| Emb[Embedder]
        Emb -->|Vectors| Qdrant[Qdrant Vector DB]
        Qdrant -->|Results| Agg[Aggregator]
    end
    
    subgraph "Offline Ingestion"
        ACL[ACL Anthology] -->|Download| Ingest[Ingestion Pipeline]
        Ingest -->|Clean & Embed| EmbModel[Embedding Model]
        EmbModel -->|Vectors| Qdrant
    end
    
    Agg -->|Ranked Papers| API
    API -->|Response| Client
```

## Supported Query Modes

### 1. Natural Language Query
**Best for:** Exploratory research, topic discovery.
- **Input:** "How do I improve low-resource translation?"
- **Process:** The system expands this into multiple semantic queries (e.g., "low-resource NMT techniques", "data augmentation for translation").

### 2. ACL Anthology Paper ID
**Best for:** Finding related work, literature review.
- **Input:** `2023.acl-long.412`
- **Process:** The system fetches the abstract of the specified paper and uses it as a semantic proxy to find other papers in the same research neighborhood.

## Offline vs Online Steps

### Offline (Ingestion)
1. **Download**: Metadata and abstracts are fetched from the ACL Anthology.
2. **Preprocess**: Text is cleaned, normalized, and formatted.
3. **Embed**: Dense vectors are generated for each abstract.
4. **Index**: Vectors are stored in Qdrant for fast retrieval.

### Online (Retrieval)
1. **Receive**: User input (text or ID) is received.
2. **Reformulate**: LLM generates multiple search queries.
3. **Retrieve**: Vector search finds candidate papers for each query.
4. **Aggregate**: Reciprocal Rank Fusion (RRF) combines and ranks results.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/nnayz/acl-anthology-rag.git
   cd acl-anthology-rag
   ```

2. **Start Infrastructure (Qdrant)**
   ```bash
   docker-compose up -d
   ```

3. **Configure Environment**
   Copy `.env.example` to `.env` in `api/` and fill in your API keys (Groq/Fireworks).
   ```bash
   cp api/.env.example api/.env
   ```

4. **Run Backend**
   ```bash
   cd api
   uv sync
   uv run fastapi dev src/app.py
   ```

5. **Run Frontend**
   ```bash
   cd client
   npm install
   npm run dev
   ```

See [Installation Guide](docs/installation.md) for detailed setup.

## Project Structure

```
.
├── api/                 # Backend (FastAPI)
│   ├── src/
│   │   ├── ingestion/   # Data processing pipeline
│   │   ├── retrieval/   # Search logic & ranking
│   │   ├── llm/         # LLM integration
│   │   └── vectorstore/ # Qdrant interface
├── client/              # Frontend (React)
├── docs/                # Documentation
└── docker-compose.yml   # Infrastructure
```

## Documentation Index

- [**Architecture**](docs/architecture.md): Deep dive into system components and design.
- [**Installation**](docs/installation.md): Detailed setup and troubleshooting.
- [**Configuration**](docs/configuration.md): Environment variables and settings.
- [**Usage**](docs/usage.md): How to use the system effectively.
- [**Workflows**](docs/workflows.md): Detailed offline and online pipeline steps.

## License

MIT License
