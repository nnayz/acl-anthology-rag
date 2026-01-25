# Installation & Setup Guide

This guide will help you set up the ACL Anthology RAG system on your local machine.

## Prerequisites

Ensure you have the following installed:

1. **Docker & Docker Compose**
   - Required for the Qdrant vector database.
   - [Install Docker](https://docs.docker.com/get-docker/)

2. **Python 3.12+**
   - Required for the backend API.
   - We recommend using `uv` for fast package management, but `pip` works too.
   - [Install Python](https://www.python.org/downloads/)
   - [Install uv](https://github.com/astral-sh/uv) (Optional but recommended)

3. **Node.js 20+**
   - Required for the React frontend.
   - [Install Node.js](https://nodejs.org/)

---

## 1. Clone the Repository

```bash
git clone https://github.com/nnayz/acl-anthology-rag.git
cd acl-anthology-rag
```

## 2. Start Infrastructure

The system uses Qdrant as a vector database. We run this via Docker.

```bash
docker-compose up -d
```

Verify Qdrant is running:
- Dashboard: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)
- API: `http://localhost:6333`

## 3. Backend Setup

Navigate to the API directory:

```bash
cd api
```

### Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your API keys. You need **at least one** of the following:
   - `GROQ_API_KEY`: For using Llama models on Groq.
   - `FIREWORKS_API_KEY`: For using models on Fireworks AI.

   *Note: Embedding is done locally by default or via API depending on configuration.*

### Install Dependencies

Using `uv` (Recommended):
```bash
uv sync
```

Or using `pip`:
```bash
pip install -r requirements.txt
# Note: You may need to generate requirements.txt from pyproject.toml if it doesn't exist
```

### Run the Server

```bash
uv run fastapi dev src/app.py
```

The API will be available at `http://localhost:8000`.
- API Docs: `http://localhost:8000/docs`

## 4. Frontend Setup

Open a new terminal and navigate to the client directory:

```bash
cd client
```

### Install Dependencies

```bash
npm install
```

### Run Development Server

```bash
npm run dev
```

The UI will be available at `http://localhost:5173`.

---

## 5. Data Ingestion (Offline Step)

Before you can search, you need to populate the database.

1. **Download & Process Data**
   The backend includes scripts to download ACL Anthology data.
   
   *Note: This process can take a significant amount of time depending on your internet connection and CPU.*

   ```bash
   # From the api/ directory
   uv run python -m src.ingestion.download
   uv run python -m src.ingestion.preprocess
   ```

2. **Generate Embeddings & Index**
   
   ```bash
   uv run python -m src.ingestion.ingest
   ```

   This will:
   - Load the processed JSON.
   - Generate embeddings for each abstract.
   - Upload them to your local Qdrant instance.

---

## Troubleshooting

### Qdrant Connection Failed
- **Error:** `Connection refused` or `Qdrant unavailable`.
- **Fix:** Ensure Docker is running. Run `docker ps` to see if the `qdrant` container is active.

### Missing API Keys
- **Error:** `ValidationError` regarding missing `GROQ_API_KEY`.
- **Fix:** Ensure `.env` exists in `api/` and contains valid keys. Restart the backend after changing `.env`.

### Ingestion Memory Issues
- **Issue:** Ingestion crashes on large datasets.
- **Fix:** Decrease `EMBEDDING_BATCH_SIZE` in `api/src/core/config.py` or via environment variable.

### Frontend API Connection
- **Issue:** UI shows "Network Error".
- **Fix:** Ensure backend is running on port 8000. Check `vite.config.ts` proxy settings if you changed ports.
