from sentence_transformers import SentenceTransformer
from src.core.config import settings

_model = None


def get_embedding_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(
            settings.EMBEDDING_MODEL,
            device="cpu",
            trust_remote_code=True,
        )
        _model.eval()
    return _model


def embed_query(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    ).tolist()
