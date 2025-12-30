⸻

# Project Scope

This document defines the scope, constraints, and boundaries of the ACL Anthology Semantic Retrieval System. It is intended to clarify both what the project aims to accomplish and what it explicitly does not attempt.

⸻

## Project Intent

This system is developed as an **academic exercise** in semantic retrieval and Retrieval-Augmented Generation (RAG) pipelines. It is designed for:

- Coursework and research demonstration
- Exploration of embedding-based retrieval techniques
- Understanding LLM-assisted query reformulation
- Experimentation with vector databases in an NLP context

The project prioritizes **conceptual clarity** and **educational value** over production-grade robustness.

⸻

## Data Scope

### What Is Included

- **Paper abstracts** from the ACL Anthology
- **Metadata** such as title, authors, publication venue, and year
- **ACL Anthology identifiers** for paper lookup

### What Is Excluded

- Full paper texts (PDFs, body content)
- Citation graphs or reference networks
- Author profiles or affiliation data beyond basic metadata
- Non-ACL venues or external corpora

The system operates **exclusively on abstracts**. This is a deliberate design choice to:

1. Reduce computational and storage requirements
2. Focus on high-signal, semantically dense content
3. Simplify the ingestion and embedding pipeline

⸻

## Functional Scope

### Supported Capabilities

| Capability | Description |
|------------|-------------|
| Natural language search | Users can query with free-form questions |
| Paper-ID similarity search | Users can provide an ACL ID to find related work |
| LLM query reformulation | All queries are expanded into multiple semantic variants |
| Vector similarity retrieval | Embedding-based search over abstract vectors |
| Result aggregation | Merging and ranking results from multiple query embeddings |

### Not Supported

| Excluded Feature | Rationale |
|------------------|-----------|
| Full-text search | Out of scope; abstracts only |
| Citation-based retrieval | No citation graph ingested |
| User accounts or sessions | No persistence of user state |
| Feedback or relevance signals | No learning from user interactions |
| Real-time corpus updates | Ingestion is a one-time offline process |

⸻

## Technical Constraints

### No Fine-Tuning

The system uses **pre-trained models only**:

- Embedding models are used as-is (no domain adaptation)
- LLMs are prompted without fine-tuning or RLHF
- No custom training loops or gradient updates

This constraint ensures reproducibility and aligns with academic resource limitations.

### No Feedback Loop

There is **no mechanism for learning from user behavior**:

- No click tracking
- No relevance judgments
- No implicit or explicit feedback collection
- No model updates based on usage

The system is stateless with respect to user interactions.

### No Production Hardening

The system is **not designed for deployment** in a production environment:

- No authentication or authorization
- No rate limiting or abuse prevention
- No high-availability architecture
- No monitoring, alerting, or observability stack
- No SLA guarantees

⸻

## What This Project Is NOT

To set clear expectations, this project explicitly **does not** aim to be:

| Not This | Explanation |
|----------|-------------|
| A production search engine | No scalability, security, or reliability guarantees |
| A complete RAG system | No answer generation or synthesis from retrieved documents |
| A citation recommendation tool | No citation graph or bibliometric analysis |
| A fine-tuned NLP model | All models are used off-the-shelf |
| A learning system | No feedback loops, no model updates, no personalization |
| A replacement for ACL Anthology search | Intended as a complementary academic experiment |
| A full-text retrieval system | Operates on abstracts only |

⸻

## Academic Context

This project is developed in the context of academic coursework and research exploration. As such:

- **Reproducibility** is prioritized over optimization
- **Simplicity** is favored over feature completeness
- **Explainability** matters more than marginal performance gains
- **Documentation** is treated as a first-class deliverable

The architecture and design choices are intended to be **defensible in an academic setting**, with clear justifications rooted in information retrieval and NLP literature.

⸻

## Summary

| Dimension | Scope |
|-----------|-------|
| Data | Abstracts and metadata only |
| Models | Pre-trained, no fine-tuning |
| Learning | None; no feedback loop |
| Deployment | Academic / local use only |
| Users | Single-user, no accounts |
| Updates | Offline ingestion, no live sync |

This document serves as the authoritative reference for what is in and out of scope for the ACL Anthology Semantic Retrieval System.

⸻

