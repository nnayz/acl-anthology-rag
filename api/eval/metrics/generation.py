"""
Generation quality metrics using LLM-as-judge (Groq Llama 3.3 70B).

Evaluates three dimensions:
- Faithfulness: Is the response grounded in retrieved abstracts?
- Answer Relevance: Does the response address the query?
- Groundedness / Citation Accuracy: Do [1], [2] citations match actual papers?
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from langchain_groq import ChatGroq

from eval.config import eval_config

logger = logging.getLogger(__name__)

FAITHFULNESS_PROMPT = """You are evaluating a RAG system's response for faithfulness to its source documents.

User query: {query}

Retrieved paper abstracts (these are the ONLY sources the system should use):
{contexts}

System response:
{response}

Evaluate faithfulness - does the response ONLY contain information that can be verified from the retrieved abstracts?

Check:
1. Are all factual claims in the response supported by the abstracts above?
2. Does the response introduce any information not present in the abstracts?
3. Are there any fabricated details, authors, years, or findings?

Score from 0.0 to 1.0:
- 1.0 = Every claim is directly supported by the abstracts
- 0.7 = Most claims supported, minor unsupported details
- 0.5 = Mix of supported and unsupported claims
- 0.3 = Many unsupported or fabricated claims
- 0.0 = Response is entirely fabricated

Return ONLY a JSON object: {{"score": <float>, "explanation": "<brief reason>"}}"""

ANSWER_RELEVANCE_PROMPT = """You are evaluating whether a RAG system's response addresses the user's query.

User query: {query}

System response:
{response}

Evaluate answer relevance - does the response address what the user asked about?

Check:
1. Does the response directly answer or address the query topic?
2. Is the information provided useful for the user's information need?
3. Does the response stay focused or go off on tangents?

Score from 0.0 to 1.0:
- 1.0 = Perfectly addresses the query with relevant information
- 0.7 = Mostly relevant with some tangential information
- 0.5 = Partially relevant, misses key aspects of the query
- 0.3 = Mostly irrelevant to the query
- 0.0 = Completely unrelated to the query

Return ONLY a JSON object: {{"score": <float>, "explanation": "<brief reason>"}}"""

GROUNDEDNESS_PROMPT = """You are evaluating a RAG system's response for citation accuracy.

The system retrieved these papers (numbered):
{papers_list}

The system generated this response:
{response}

Evaluate citation accuracy:
1. Does every citation [N] in the response correspond to paper N in the list above?
2. Are the facts attributed to each cited paper actually present in that paper's abstract?
3. Does the response make any claims not supported by the retrieved papers?

Score from 0.0 to 1.0:
- 1.0 = All citations are accurate, all claims are grounded
- 0.7 = Most citations accurate, minor attribution errors
- 0.5 = Some citations accurate, some claims ungrounded
- 0.3 = Many citation errors or ungrounded claims
- 0.0 = Citations are fabricated or claims are hallucinated

Return ONLY a JSON object: {{"score": <float>, "explanation": "<brief reason>"}}"""


def _get_judge_llm() -> ChatGroq:
    """Create a judge LLM instance (separate from pipeline's 8B model)."""
    return ChatGroq(
        model=eval_config.JUDGE_MODEL,
        temperature=eval_config.JUDGE_TEMPERATURE,
        max_tokens=eval_config.JUDGE_MAX_TOKENS,
    )


async def _call_judge(prompt: str) -> Dict[str, Any]:
    """Call the LLM judge and parse JSON response."""
    llm = _get_judge_llm()

    try:
        response = await llm.ainvoke(prompt)
        content = response.content.strip()

        # Handle markdown code blocks
        if content.startswith("```"):
            content = content.split("\n", 1)[1]  # Remove first line
            content = content.rsplit("```", 1)[0]  # Remove last ```
            content = content.strip()

        result = json.loads(content)
        return result
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse judge response as JSON: {e}")
        return {"score": 0.0, "explanation": f"JSON parse error: {e}"}
    except Exception as e:
        logger.error(f"Judge call failed: {e}")
        return {"score": 0.0, "explanation": f"Judge error: {e}"}


async def evaluate_faithfulness(
    query: str,
    response: str,
    contexts: List[str],
) -> Dict[str, Any]:
    """
    Evaluate if the response is grounded in retrieved abstracts.

    Args:
        query: The user's search query
        response: The system's generated response
        contexts: List of abstract texts from retrieved papers

    Returns:
        Dict with score (0-1) and explanation
    """
    contexts_text = "\n\n".join(
        f"Abstract {i+1}: {ctx[:500]}" for i, ctx in enumerate(contexts) if ctx
    )
    if not contexts_text:
        contexts_text = "(No abstracts available)"

    prompt = FAITHFULNESS_PROMPT.format(
        query=query,
        contexts=contexts_text,
        response=response,
    )

    return await _call_judge(prompt)


async def evaluate_answer_relevance(
    query: str,
    response: str,
) -> Dict[str, Any]:
    """
    Evaluate if the response addresses the user's query.

    Args:
        query: The user's search query
        response: The system's generated response

    Returns:
        Dict with score (0-1) and explanation
    """
    prompt = ANSWER_RELEVANCE_PROMPT.format(
        query=query,
        response=response,
    )

    return await _call_judge(prompt)


async def evaluate_groundedness(
    query: str,
    response: str,
    papers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate citation accuracy in the response.

    Args:
        query: The user's search query
        response: The system's generated response
        papers: List of paper metadata dicts with title, abstract, year, authors

    Returns:
        Dict with score (0-1) and explanation
    """
    papers_list = "\n".join(
        f"Paper {i+1}: {p.get('title', 'Unknown')} ({p.get('year', 'N/A')}) - "
        f"Abstract: {(p.get('abstract') or 'N/A')[:300]}..."
        for i, p in enumerate(papers)
    )

    prompt = GROUNDEDNESS_PROMPT.format(
        papers_list=papers_list,
        response=response,
    )

    return await _call_judge(prompt)


async def evaluate_all_generation_metrics(
    query: str,
    response: str,
    papers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Run all generation quality metrics.

    Args:
        query: The user's search query
        response: The system's generated response
        papers: List of paper metadata dicts

    Returns:
        Dict with faithfulness, answer_relevance, groundedness scores
    """
    contexts = [p.get("abstract", "") for p in papers]

    # Run judge calls sequentially to respect Groq rate limits
    faithfulness = await evaluate_faithfulness(query, response, contexts)
    await asyncio.sleep(eval_config.JUDGE_DELAY_SECONDS)

    relevance = await evaluate_answer_relevance(query, response)
    await asyncio.sleep(eval_config.JUDGE_DELAY_SECONDS)

    groundedness = await evaluate_groundedness(query, response, papers)

    return {
        "faithfulness": faithfulness,
        "answer_relevance": relevance,
        "groundedness": groundedness,
    }
