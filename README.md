⸻

ACL Anthology Semantic Retrieval System

This project implements a semantic retrieval system over the ACL Anthology corpus. The goal is to help users discover relevant NLP research papers using either natural language questions or ACL Anthology paper identifiers.

The system is designed as a lightweight Retrieval-Augmented Generation (RAG) style pipeline, suitable for academic experimentation rather than production deployment.

⸻

Problem Motivation

The ACL Anthology contains tens of thousands of NLP research papers. Traditional keyword search struggles with semantic understanding, paraphrases, and conceptual similarity.

This project addresses that by:
	•	Representing paper abstracts as dense vector embeddings
	•	Using semantic similarity search instead of keyword matching
	•	Supporting both free-form questions and paper-based similarity search

⸻

Supported Query Modes

The system supports two query modalities, both of which ultimately use the same retrieval pipeline.

1. Natural Language Query

Users can ask questions such as:
	•	“Papers on low-resource neural machine translation”
	•	“Work on multilingual transfer learning for NLP”

This mode is intended for exploratory research and topic discovery.

2. ACL Anthology Paper ID Query

Users can also provide a specific ACL Anthology identifier, for example:
	•	2023.acl-long.412

In this case, the system retrieves the corresponding paper’s abstract and uses it as a semantic proxy to find similar papers.

⸻

Core Design Principle

All queries are converted into semantic search queries using an LLM before vector retrieval.

The system never embeds the raw user query directly. Instead, it uses an LLM to reformulate the input into multiple focused search queries. This improves recall and captures different semantic facets of the information need.

This principle applies equally to both query modes.

⸻

Data Preparation Workflow

Before user interaction, the system performs an offline ingestion step:
	1.	Abstracts and metadata are collected from the ACL Anthology.
	2.	Each abstract is cleaned and normalized.
	3.	Dense vector embeddings are generated for each abstract.
	4.	The embeddings and metadata are stored in a vector database.

Only abstracts are stored and embedded. Full paper texts are not used.

⸻

Query Processing Workflow

Step 1: Input Interpretation
	•	If the user provides natural language, the text is passed directly to the LLM.
	•	If the user provides a paper ID, the system first retrieves the paper’s abstract and metadata.

Step 2: Query Reformulation

An LLM generates multiple semantically meaningful search queries based on the input. These queries may include:
	•	Paraphrases
	•	Subtopic-focused queries
	•	Keyword-style expansions

This step allows the system to better cover the semantic space of the user’s intent.

Step 3: Embedding

Each reformulated query is converted into a vector embedding using the same embedding model used for the abstracts.

Step 4: Vector Retrieval

For each query embedding:
	•	A similarity search is performed against the abstract embeddings.
	•	Top-k candidate papers are retrieved.

Step 5: Result Aggregation

Results from all query embeddings are merged and ranked to produce a final list of relevant papers.

⸻

Why Use Paper Abstracts as Queries

In the paper-ID mode, the abstract functions as a rich semantic representation of the paper’s contribution. Using it as input to the query reformulation step enables:
	•	Document-to-document similarity search
	•	Discovery of related work
	•	Exploration of research neighborhoods

This approach aligns with classical information retrieval concepts such as document-as-query retrieval.

⸻

Architectural Advantages
	•	A single unified retrieval pipeline for all query types
	•	No special-case logic after query interpretation
	•	Clear separation between ingestion and querying
	•	Easy to explain and justify academically

⸻

Mermaid Workflow Diagram

flowchart TD
    A[User Input] --> B{Query Type}

    B -->|Natural Language| C[LLM Query Reformulation]
    B -->|ACL Paper ID| D[Fetch Paper Abstract]
    D --> C

    C --> E[Multiple Reformulated Queries]
    E --> F[Query Embeddings]

    F --> G[Vector Database<br/>Abstract Embeddings]
    G --> H[Top-K Similar Papers]

    H --> I[Rank & Aggregate Results]
    I --> J[Final Response to User]


⸻

Project Structure

The backend API follows a modular architecture aligned with the system's workflow stages.

api/src/
├── main.py              # Application entry point
├── api/                 # HTTP interface (FastAPI)
│   ├── app.py           # FastAPI application setup
│   └── routes.py        # API endpoint definitions
├── core/                # Shared components
│   ├── config.py        # Configuration management
│   └── schemas.py       # Pydantic data models
├── ingestion/           # Offline data preparation
│   ├── download.py      # ACL Anthology data fetching
│   ├── preprocess.py    # Text cleaning and normalization
│   ├── embed.py         # Embedding generation
│   └── ingest.py        # Pipeline orchestration
├── retrieval/           # Query-time processing
│   ├── query_processor.py   # Query interpretation
│   ├── aggregator.py        # Result merging and ranking
│   └── pipeline.py          # Retrieval orchestration
├── llm/                 # LLM integration
│   ├── reformulator.py  # Query expansion
│   └── prompts.py       # Prompt templates
└── vectorstore/         # Vector database interface
    └── client.py        # Qdrant client wrapper

Naming Conventions
	•	Modules: lowercase with underscores (e.g., query_processor.py)
	•	Classes: PascalCase (e.g., QueryProcessor)
	•	Functions: lowercase with underscores (e.g., process_query)
	•	Constants: UPPERCASE with underscores (e.g., DEFAULT_TOP_K)
	•	Config files: lowercase (e.g., config.py, .env)

⸻

Scope and Limitations
	•	The system operates only on abstracts, not full texts.
	•	It is intended for academic use and demonstration.
	•	No fine-tuning or feedback learning is included.
	•	Response generation is limited to retrieval and presentation.

⸻

Summary

This project demonstrates how semantic retrieval over scientific literature can be achieved using modern embedding models and LLM-based query reformulation. By unifying natural language and document-based queries into a single pipeline, the system provides a clean and conceptually strong approach to research paper discovery.

⸻