from typing import Optional, List
from qdrant_client.models import Filter, FieldCondition, MatchValue
from src.vectorstore.client import get_qdrant_client

COLLECTION = "acl-anthology"


def fetch_paper_by_id(paper_id: str) -> Optional[dict]:
    client = get_qdrant_client(timeout=30.0)

    points, _ = client.scroll(
        collection_name=COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="paper_id",
                    match=MatchValue(value=paper_id),
                )
            ]
        ),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )

    if not points:
        return None

    return points[0].payload


def search_similar(embedding: list[float], top_k: int) -> List[dict]:
    client = get_qdrant_client(timeout=30.0)

    hits = client.search(
        collection_name=COLLECTION,
        query_vector=embedding,
        limit=top_k,
        with_payload=True,
    )

    results = []
    seen = set()

    for rank, hit in enumerate(hits, start=1):
        pid = hit.payload.get("paper_id")
        if pid in seen:
            continue
        seen.add(pid)

        results.append({
            "rank": rank,
            "paper_id": pid,
            "title": hit.payload.get("title"),
            "score": hit.score,
        })

    return results
