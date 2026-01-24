"""
Prompt templates for LLM interactions.

This module contains the prompt templates used for query
reformulation and any other LLM-based operations. Prompts
are designed to elicit focused, search-oriented outputs.
"""

from langchain_core.prompts import ChatPromptTemplate

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
    return ChatPromptTemplate.from_messages([
        ("system", REFORMULATION_SYSTEM_PROMPT),
        ("human", REFORMULATION_HUMAN_PROMPT),
    ])


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
    return ChatPromptTemplate.from_messages([
        ("system", PAPER_CONTEXT_SYSTEM_PROMPT),
        ("human", PAPER_CONTEXT_HUMAN_PROMPT),
    ])
