"""
LLM-based query reformulation.

This module uses an LLM to expand user queries into multiple
semantically meaningful search queries. This improves recall
by capturing different facets of the user's information need.

The reformulator uses LangChain's LCEL (LangChain Expression Language)
with RunnableWithFallbacks for robust error handling.
"""

import logging
from typing import Any, List, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langchain_groq import ChatGroq

from src.core.config import settings
from src.llm.prompts import get_reformulation_prompt, get_paper_context_prompt

logger = logging.getLogger(__name__)


def _create_fallback_runnable(fallback_value: Any) -> RunnableLambda:
    """Create a runnable that returns a constant fallback value."""
    return RunnableLambda(lambda _: fallback_value)


class QueryReformulator:
    """
    Reformulates user queries into multiple search queries using an LLM.

    Uses LangChain's LCEL with RunnableWithFallbacks for robust error handling:
    1. Takes a user query (or paper context)
    2. Passes it through a prompt template
    3. Calls the Groq LLM
    4. Parses the JSON output into a list of queries
    5. Falls back gracefully on errors

    Attributes:
        llm: The Groq LLM instance
        num_queries: Number of reformulated queries to generate
        reformulation_chain: LCEL chain with fallback for NL queries
        paper_context_chain: LCEL chain with fallback for paper queries
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        num_queries: Optional[int] = None,
    ):
        """
        Initialize the query reformulator.

        Args:
            model_name: Groq model to use (default: from settings)
            temperature: LLM temperature (default: from settings)
            num_queries: Number of reformulated queries (default: from settings)
        """
        self.num_queries = num_queries or settings.NUM_REFORMULATED_QUERIES
        self._model_name = model_name or settings.GROQ_MODEL
        self._temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE

        # Initialize Groq LLM (reads GROQ_API_KEY from environment)
        self.llm = ChatGroq(
            model=self._model_name,
            temperature=self._temperature,
            max_tokens=settings.LLM_MAX_TOKENS,
        )

        # JSON output parser
        self.parser = JsonOutputParser()

        # Build LCEL chains with fallbacks
        self._build_chains()

    def _build_chains(self):
        """Build the LCEL chains with fallback handling."""
        # Base chain for natural language query reformulation
        base_reformulation_chain = (
            get_reformulation_prompt()
            | self.llm
            | self.parser
        )

        # Wrap with fallback that returns empty list (caller adds original query)
        self.reformulation_chain: RunnableWithFallbacks = base_reformulation_chain.with_fallbacks(
            [_create_fallback_runnable([])],
            exceptions_to_handle=(Exception,),
        )

        # Base chain for paper-based query generation
        base_paper_context_chain = (
            get_paper_context_prompt()
            | self.llm
            | self.parser
        )

        # Wrap with fallback - caller will use title as backup
        self.paper_context_chain: RunnableWithFallbacks = base_paper_context_chain.with_fallbacks(
            [_create_fallback_runnable(None)],
            exceptions_to_handle=(Exception,),
        )

    async def reformulate(self, query: str) -> List[str]:
        """
        Reformulate a natural language query into multiple search queries.

        Args:
            query: The user's original search query

        Returns:
            List of reformulated queries (includes original query as first item)
        """
        reformulated = await self.reformulation_chain.ainvoke({
            "query": query,
            "num_queries": self.num_queries,
        })

        # Validate output and prepend original query
        if isinstance(reformulated, list) and reformulated:
            return [query] + reformulated[:self.num_queries]

        if reformulated is None or reformulated == []:
            logger.warning("Reformulation returned empty, using original query only")
        else:
            logger.warning(f"Unexpected reformulation output: {type(reformulated)}")

        return [query]

    async def reformulate_from_paper(
        self,
        title: str,
        abstract: str,
    ) -> List[str]:
        """
        Generate search queries based on a paper's content.

        Used when user provides a paper ID instead of a search query.

        Args:
            title: Paper title
            abstract: Paper abstract

        Returns:
            List of generated search queries
        """
        queries = await self.paper_context_chain.ainvoke({
            "title": title,
            "abstract": abstract,
            "num_queries": self.num_queries,
        })

        # Validate output
        if isinstance(queries, list) and queries:
            return queries[:self.num_queries]

        if queries is None:
            logger.warning("Paper context generation returned None, using title")
        else:
            logger.warning(f"Unexpected paper context output: {type(queries)}")

        # Fallback: use title as query
        return [title]


# Module-level singleton for reuse
_reformulator: Optional[QueryReformulator] = None


def get_reformulator() -> QueryReformulator:
    """Get or create the singleton QueryReformulator instance."""
    global _reformulator
    if _reformulator is None:
        _reformulator = QueryReformulator()
    return _reformulator
