# Usage Guide

This document explains how to use the ACL Anthology RAG system effectively, covering both user interface interactions and the different query modes available.

## Accessing the Interface

Once the system is running (see [Installation](installation.md)), navigate to:
- **Frontend:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000/docs` (Swagger UI)

## Query Modes

The system supports two distinct ways to search for papers. The interface automatically detects or allows you to select the mode.

### 1. Natural Language Search

This is the standard search mode. You describe what you are looking for in plain English.

**Best for:**
- Exploring a new topic.
- Finding papers when you don't know the specific terminology.
- Answering "What is..." or "How to..." questions.

**Examples:**
- *"What are the latest techniques in zero-shot classification?"*
- *"Papers discussing bias in large language models."*
- *"History of dependency parsing 2010-2020."*

**How it works:**
The system uses an LLM to "brainstorm" different ways to ask your question. It might generate queries like *"zero-shot learning methods"*, *"unsupervised classification"*, and *"cross-lingual zero-shot"*. This ensures you get results even if you didn't use the exact keywords found in the papers.

---

### 2. Paper ID Search ("Paper as Query")

In this mode, you provide a specific ACL Anthology ID. The system uses that paper's abstract to find *other* papers that are semantically similar.

**Best for:**
- Literature reviews.
- Finding "more like this".
- Discovering papers in the same research cluster.

**Input Format:**
- Use the standard ACL ID format: `YYYY.venue-type.number`
- Example: `2023.acl-long.412`

**How it works:**
1. You enter `2023.acl-long.412`.
2. The system looks up the abstract for that paper.
3. It treats that abstract as a very long, detailed query.
4. It retrieves papers that share similar vector embeddings—meaning they cover similar concepts, methods, or topics.

---

## Understanding Results

The search results display a list of papers ranked by relevance.

**Each result card shows:**
- **Title**: Link to the paper on ACL Anthology.
- **Year & Venue**: E.g., "ACL 2023".
- **Similarity Score**: A value indicating how closely it matched your query.
- **Abstract**: A snippet or full text of the abstract.

**Interpreting Scores:**
- Scores are relative. A higher score means better semantic match.
- Because of the fusion algorithm (RRF), scores might not be simple cosine similarities (0-1), but rather a ranking score.

## Advanced Usage (API)

You can interact directly with the backend via HTTP requests.

**Endpoint:** `POST /search`

**Payload:**
```json
{
  "query": "explain attention mechanisms",
  "mode": "natural_language",
  "top_k": 10
}
```

**Payload for Paper ID:**
```json
{
  "query": "2023.acl-long.412",
  "mode": "paper_id",
  "top_k": 10
}
```
