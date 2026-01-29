"""
Prompt templates for LLM interactions.

This module contains the prompt templates used for query
reformulation and any other LLM-based operations. Prompts
are designed to elicit focused, search-oriented outputs.
"""

from langchain_core.prompts import ChatPromptTemplate

# =====================
# Filter Extraction Prompts
# =====================

FILTER_EXTRACTION_SYSTEM_PROMPT = """You are an expert at parsing academic paper search queries into structured filters.

Your task is to extract structured filters from natural language queries about academic papers in computational linguistics and NLP.

Available filters:
- year: Extract exact year OR year range (min_year, max_year)
  - "from 2017" -> min_year: 2017
  - "papers in 2020" -> exact: 2020
  - "between 2018 and 2022" -> min_year: 2018, max_year: 2022
  - "recent papers" or "latest" -> min_year: (current_year - 2)
  - "last 5 years" -> min_year: (current_year - 5)
- authors: List of author names mentioned (partial names OK)
  - "by Vaswani" -> ["Vaswani"]
  - "papers by Smith and Jones" -> ["Smith", "Jones"]
- title_keywords: Specific words that must appear in the title
  - "titled 'attention'" -> ["attention"]
  - Only use for explicit title mentions, not general topic words
- language: Language of the paper (if explicitly mentioned)
  - "papers in English" -> "en"
  - "Chinese language papers" -> "zh"
- has_awards: true if query mentions award-winning papers
  - "best paper", "award-winning" -> true
- awards: Specific award names if mentioned
  - "best paper award" -> ["Best Paper"]
- bibkey: ACL anthology bibkey if explicitly mentioned
  - "vaswani-etal-2017-attention" -> exact match

IMPORTANT:
- Only extract filters that are EXPLICITLY mentioned or strongly implied
- Do NOT assume filters from general topic words
- Topic words like "transformers", "NMT", "BERT" are NOT title_keywords - they go in semantic_query
- Return null for semantic_query if ONLY filters are requested (no topic/concept search)
- Return the semantic_query as the core search intent stripped of filter-related words

Return ONLY valid JSON with this exact structure:
{{
  "filters": {{
    "year": {{"exact": int|null, "min_year": int|null, "max_year": int|null}} | null,
    "authors": ["name1", "name2"] | null,
    "title_keywords": ["word1"] | null,
    "language": "code" | null,
    "has_awards": true | null,
    "awards": ["award1"] | null,
    "bibkey": "exact-bibkey" | null
  }},
  "semantic_query": "remaining search intent" | null
}}"""

FILTER_EXTRACTION_HUMAN_PROMPT = """Query: {query}
Current year: {current_year}

Parse this query into structured filters and remaining semantic search intent:"""


def get_filter_extraction_prompt() -> ChatPromptTemplate:
    """
    Returns the ChatPromptTemplate for filter extraction from natural language.

    The prompt instructs the LLM to parse a query into structured filters
    and identify the remaining semantic search intent.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", FILTER_EXTRACTION_SYSTEM_PROMPT),
            ("human", FILTER_EXTRACTION_HUMAN_PROMPT),
        ]
    )


# =====================
# Query Reformulation Prompts
# =====================

# System prompt for query reformulation
REFORMULATION_SYSTEM_PROMPT = """You are a query reformulation expert for academic paper search in computational linguistics and NLP.

Your task is to expand the user's query into {num_queries} semantically diverse search queries that:
1. Capture different aspects or phrasings of the information need
2. Use domain-specific terminology from NLP/computational linguistics
3. Include synonyms, related concepts, and alternative formulations
4. Are suitable for semantic similarity search over paper abstracts

Return ONLY a JSON array of strings with exactly {num_queries} reformulated queries.
Do not include explanations or additional text."""

REFORMULATION_HUMAN_PROMPT = """Original query: {query}

Generate {num_queries} search queries:"""


def get_reformulation_prompt() -> ChatPromptTemplate:
    """
    Returns the ChatPromptTemplate for query reformulation.

    The prompt instructs the LLM to generate multiple semantically
    diverse queries from a single user query.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", REFORMULATION_SYSTEM_PROMPT),
            ("human", REFORMULATION_HUMAN_PROMPT),
        ]
    )


# Prompt for paper ID context expansion (when searching by paper ID)
PAPER_CONTEXT_SYSTEM_PROMPT = """You are an expert at understanding academic papers in NLP and computational linguistics.

Given a paper's title and abstract, generate {num_queries} search queries that would find:
1. Papers on similar topics or methods
2. Papers that might cite or be cited by this paper
3. Papers using similar techniques or datasets
4. Papers addressing related research questions

Return ONLY a JSON array of strings with exactly {num_queries} search queries."""

PAPER_CONTEXT_HUMAN_PROMPT = """Paper Title: {title}
Abstract: {abstract}

Generate {num_queries} related paper search queries:"""


def get_paper_context_prompt() -> ChatPromptTemplate:
    """
    Returns the ChatPromptTemplate for paper-based query generation.

    Used when the user provides a paper ID - generates queries based
    on the paper's content to find similar papers.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", PAPER_CONTEXT_SYSTEM_PROMPT),
            ("human", PAPER_CONTEXT_HUMAN_PROMPT),
        ]
    )


# Prompt for synthesizing a natural language response from search results
RESPONSE_SYNTHESIS_SYSTEM_PROMPT = """You are a helpful research assistant for the ACL Anthology, a comprehensive database of computational linguistics and NLP papers.

Your task is to provide a natural, informative response based on the search results. Your response should:
1. Directly address the user's query
2. Summarize key findings from the relevant papers
3. Highlight connections between papers when applicable
4. Be concise but informative

CRITICAL: Use inline citations with bracketed NUMBERS like [1], [2], [3], etc. The number corresponds to "Paper 1", "Paper 2", etc. in the search results below. Do NOT use paper IDs as citations - only use simple numbers.

Format your response using markdown:
- Use **bold** for paper titles followed by the citation NUMBER, e.g., **Attention Is All You Need** [1]
- Include the year and authors inline
- Add brief descriptions of each paper's relevance
- You can reference multiple papers together like [1, 2]

Example format:
"Recent work on transformers includes **Attention Is All You Need** [1] by Vaswani et al. (2017), which introduced the self-attention mechanism. Building on this, **BERT** [2] demonstrated the power of pre-training..."

Keep your response focused and scholarly in tone."""

RESPONSE_SYNTHESIS_HUMAN_PROMPT = """User query: {query}

Search results (ranked by relevance):
{results_text}

Provide a helpful response summarizing these papers and how they relate to the user's query:"""


def get_response_synthesis_prompt() -> ChatPromptTemplate:
    """
    Returns the ChatPromptTemplate for response synthesis.

    Used to generate a natural language response from search results.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", RESPONSE_SYNTHESIS_SYSTEM_PROMPT),
            ("human", RESPONSE_SYNTHESIS_HUMAN_PROMPT),
        ]
    )


# Prompt for synthesizing responses for paper ID queries (similar papers)
SIMILAR_PAPERS_SYNTHESIS_SYSTEM_PROMPT = """You are a helpful research assistant for the ACL Anthology.

The user has provided a specific paper and wants to find similar papers. Your task is to:
1. Briefly acknowledge the source paper
2. Explain how the similar papers relate to it
3. Highlight methodological or topical connections

CRITICAL: Use inline citations with bracketed NUMBERS like [1], [2], [3], etc. The number corresponds to "Paper 1", "Paper 2", etc. in the search results below. Do NOT use paper IDs as citations - only use simple numbers.

Format your response using markdown:
- Use **bold** for paper titles followed by the citation NUMBER, e.g., **Paper Title** [1]
- Include year and authors inline
- Add brief descriptions of similarity/relevance
- You can reference multiple papers together like [1, 2]

Example format:
"Based on the source paper's focus on word segmentation, I found several related works. **Chinese Word Segmentation** [1] by Zhang et al. (2020) uses a similar BERT-based approach..."

Be concise but informative. Focus on the connections between papers."""

SIMILAR_PAPERS_SYNTHESIS_HUMAN_PROMPT = """Source paper the user is interested in:
- Title: {source_title}
- Authors: {source_authors}
- Year: {source_year}
- Abstract: {source_abstract}

Similar papers found:
{results_text}

Provide a response explaining how these papers relate to the source paper:"""


def get_similar_papers_synthesis_prompt() -> ChatPromptTemplate:
    """
    Returns the ChatPromptTemplate for similar papers response synthesis.

    Used when the user provides a paper ID and wants similar papers.
    """
    return ChatPromptTemplate.from_messages(
        [
            ("system", SIMILAR_PAPERS_SYNTHESIS_SYSTEM_PROMPT),
            ("human", SIMILAR_PAPERS_SYNTHESIS_HUMAN_PROMPT),
        ]
    )
