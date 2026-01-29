"""
LLM-based query reformulation.

This module uses an LLM to expand user queries into multiple
semantically meaningful search queries. This improves recall
by capturing different facets of the user's information need.

The reformulator uses LangChain's LCEL (LangChain Expression Language)
with RunnableWithFallbacks for robust error handling.
"""

import logging
from typing import Any, AsyncIterator, List, Optional

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langchain_groq import ChatGroq

from src.core.config import settings
from src.core.schemas import PaperMetadata, SearchResult
from src.llm.prompts import (
    get_reformulation_prompt,
    get_paper_context_prompt,
    get_response_synthesis_prompt,
    get_similar_papers_synthesis_prompt,
)

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
        self._temperature = (
            temperature if temperature is not None else settings.LLM_TEMPERATURE
        )

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
        base_reformulation_chain = get_reformulation_prompt() | self.llm | self.parser

        # Wrap with fallback that returns empty list (caller adds original query)
        self.reformulation_chain: RunnableWithFallbacks = (
            base_reformulation_chain.with_fallbacks(
                [_create_fallback_runnable([])],
                exceptions_to_handle=(Exception,),
            )
        )

        # Base chain for paper-based query generation
        base_paper_context_chain = get_paper_context_prompt() | self.llm | self.parser

        # Wrap with fallback - caller will use title as backup
        self.paper_context_chain: RunnableWithFallbacks = (
            base_paper_context_chain.with_fallbacks(
                [_create_fallback_runnable(None)],
                exceptions_to_handle=(Exception,),
            )
        )

    async def reformulate(self, query: str) -> List[str]:
        """
        Reformulate a natural language query into multiple search queries.

        Args:
            query: The user's original search query

        Returns:
            List of reformulated queries (includes original query as first item)
        """
        reformulated = await self.reformulation_chain.ainvoke(
            {
                "query": query,
                "num_queries": self.num_queries,
            }
        )

        # Validate output and prepend original query
        if isinstance(reformulated, list) and reformulated:
            return [query] + reformulated[: self.num_queries]

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
        queries = await self.paper_context_chain.ainvoke(
            {
                "title": title,
                "abstract": abstract,
                "num_queries": self.num_queries,
            }
        )

        # Validate output
        if isinstance(queries, list) and queries:
            return queries[: self.num_queries]

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


class ResponseSynthesizer:
    """
    Synthesizes natural language responses from search results using an LLM.

    Takes search results and the original query, then generates a helpful,
    markdown-formatted response that summarizes the findings.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """
        Initialize the response synthesizer.

        Args:
            model_name: Groq model to use (default: from settings)
            temperature: LLM temperature (default: from settings)
        """
        self._model_name = model_name or settings.GROQ_MODEL
        self._temperature = (
            temperature if temperature is not None else settings.LLM_TEMPERATURE
        )

        # Initialize Groq LLM
        self.llm = ChatGroq(
            model=self._model_name,
            temperature=self._temperature,
            max_tokens=1024,  # Allow longer responses for synthesis
        )

        # Build the synthesis chain
        self._build_chain()

    def _build_chain(self):
        """Build the LCEL chains for response synthesis."""
        from langchain_core.output_parsers import StrOutputParser

        # Chain for general search queries
        base_chain = get_response_synthesis_prompt() | self.llm | StrOutputParser()

        # Wrap with fallback that returns a simple formatted response
        self.synthesis_chain: RunnableWithFallbacks = base_chain.with_fallbacks(
            [_create_fallback_runnable(None)],
            exceptions_to_handle=(Exception,),
        )

        # Chain for similar papers queries (paper ID based)
        similar_papers_chain = (
            get_similar_papers_synthesis_prompt() | self.llm | StrOutputParser()
        )

        self.similar_papers_chain: RunnableWithFallbacks = (
            similar_papers_chain.with_fallbacks(
                [_create_fallback_runnable(None)],
                exceptions_to_handle=(Exception,),
            )
        )

    def _format_results_for_prompt(self, results: List[SearchResult]) -> str:
        """Format search results into a text representation for the LLM prompt."""
        if not results:
            return "No results found."

        formatted_parts = []
        for i, result in enumerate(results, 1):
            paper = result.paper
            authors = (
                ", ".join(paper.authors[:3]) if paper.authors else "Unknown authors"
            )
            if paper.authors and len(paper.authors) > 3:
                authors += " et al."

            part = f"""Paper {i}:
- Title: {paper.title}
- Authors: {authors}
- Year: {paper.year or 'N/A'}
- Paper ID: {paper.paper_id}
- PDF: {paper.pdf_url or 'Not available'}
- Relevance Score: {result.score:.0%}
- Abstract: {paper.abstract or 'No abstract available'}
"""
            formatted_parts.append(part)

        return "\n".join(formatted_parts)

    def _generate_fallback_response(
        self,
        query: str,
        results: List[SearchResult],
    ) -> str:
        """Generate a simple fallback response if LLM fails."""
        if not results:
            return "No papers found matching your query. Try a different search term."

        lines = [f"Found {len(results)} relevant papers for your query:\n"]

        for i, result in enumerate(results, 1):
            paper = result.paper
            authors = (
                ", ".join(paper.authors[:3]) if paper.authors else "Unknown authors"
            )
            if paper.authors and len(paper.authors) > 3:
                authors += " et al."

            lines.append(f"**{i}. {paper.title}**")
            lines.append(f"   - {authors} ({paper.year or 'N/A'})")
            if paper.pdf_url:
                lines.append(f"   - [PDF]({paper.pdf_url})")
            lines.append("")

        return "\n".join(lines)

    def _generate_similar_papers_fallback(
        self,
        source_paper: PaperMetadata,
        results: List[SearchResult],
    ) -> str:
        """Generate a fallback response for similar papers query."""
        if not results:
            return f"I couldn't find papers similar to **{source_paper.title}**. The paper may be too specialized or not well represented in the database."

        lines = [f"Found {len(results)} papers similar to **{source_paper.title}**:\n"]

        for i, result in enumerate(results, 1):
            paper = result.paper
            authors = (
                ", ".join(paper.authors[:3]) if paper.authors else "Unknown authors"
            )
            if paper.authors and len(paper.authors) > 3:
                authors += " et al."

            lines.append(f"**{i}. {paper.title}**")
            lines.append(f"   - {authors} ({paper.year or 'N/A'})")
            lines.append(f"   - Similarity: {result.score:.0%}")
            if paper.pdf_url:
                lines.append(f"   - [PDF]({paper.pdf_url})")
            lines.append("")

        return "\n".join(lines)

    async def synthesize(
        self,
        query: str,
        results: List[SearchResult],
        source_paper: Optional[PaperMetadata] = None,
    ) -> str:
        """
        Synthesize a natural language response from search results.

        Args:
            query: The original user query
            results: List of search results
            source_paper: Optional source paper for paper ID queries

        Returns:
            Markdown-formatted response string
        """
        if not results:
            if source_paper:
                return f"I couldn't find papers similar to **{source_paper.title}**. Try a different paper ID or a text-based search."
            return "I couldn't find any papers matching your query. Try rephrasing or using different keywords."

        results_text = self._format_results_for_prompt(results)

        # Use different chain for paper ID queries
        if source_paper:
            source_authors = (
                ", ".join(source_paper.authors[:3])
                if source_paper.authors
                else "Unknown authors"
            )
            if source_paper.authors and len(source_paper.authors) > 3:
                source_authors += " et al."

            response = await self.similar_papers_chain.ainvoke(
                {
                    "source_title": source_paper.title,
                    "source_authors": source_authors,
                    "source_year": source_paper.year or "N/A",
                    "source_abstract": source_paper.abstract or "No abstract available",
                    "results_text": results_text,
                }
            )

            if response is None:
                logger.warning("Similar papers synthesis failed, using fallback")
                return self._generate_similar_papers_fallback(source_paper, results)

            return response

        # Standard synthesis for natural language queries
        response = await self.synthesis_chain.ainvoke(
            {
                "query": query,
                "results_text": results_text,
            }
        )

        # If LLM failed, use fallback
        if response is None:
            logger.warning("Response synthesis failed, using fallback")
            return self._generate_fallback_response(query, results)

        return response

    async def synthesize_stream(
        self,
        query: str,
        results: List[SearchResult],
        source_paper: Optional[PaperMetadata] = None,
    ) -> AsyncIterator[str]:
        """
        Stream a natural language response from search results.

        Yields chunks of the response as they are generated by the LLM.

        Args:
            query: The original user query
            results: List of search results
            source_paper: Optional source paper for paper ID queries

        Yields:
            String chunks of the response
        """
        if not results:
            if source_paper:
                yield f"I couldn't find papers similar to **{source_paper.title}**. Try a different paper ID or a text-based search."
            else:
                yield "I couldn't find any papers matching your query. Try rephrasing or using different keywords."
            return

        results_text = self._format_results_for_prompt(results)

        try:
            if source_paper:
                # Streaming for paper ID queries
                source_authors = (
                    ", ".join(source_paper.authors[:3])
                    if source_paper.authors
                    else "Unknown authors"
                )
                if source_paper.authors and len(source_paper.authors) > 3:
                    source_authors += " et al."

                prompt = get_similar_papers_synthesis_prompt()
                messages = prompt.format_messages(
                    source_title=source_paper.title,
                    source_authors=source_authors,
                    source_year=source_paper.year or "N/A",
                    source_abstract=source_paper.abstract or "No abstract available",
                    results_text=results_text,
                )

                async for chunk in self.llm.astream(messages):
                    if chunk.content:
                        yield chunk.content
            else:
                # Streaming for natural language queries
                prompt = get_response_synthesis_prompt()
                messages = prompt.format_messages(
                    query=query,
                    results_text=results_text,
                )

                async for chunk in self.llm.astream(messages):
                    if chunk.content:
                        yield chunk.content

        except Exception as e:
            logger.error(f"Streaming synthesis failed: {e}")
            # Fall back to non-streaming response
            if source_paper:
                yield self._generate_similar_papers_fallback(source_paper, results)
            else:
                yield self._generate_fallback_response(query, results)


# Module-level singleton for response synthesizer
_synthesizer: Optional[ResponseSynthesizer] = None


def get_synthesizer() -> ResponseSynthesizer:
    """Get or create the singleton ResponseSynthesizer instance."""
    global _synthesizer
    if _synthesizer is None:
        _synthesizer = ResponseSynthesizer()
    return _synthesizer
