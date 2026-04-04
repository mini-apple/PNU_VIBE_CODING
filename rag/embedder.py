from __future__ import annotations

import os

from langchain_openai import OpenAIEmbeddings

_embeddings: OpenAIEmbeddings | None = None


def get_embeddings() -> OpenAIEmbeddings:
    global _embeddings
    if _embeddings is None:
        _embeddings = OpenAIEmbeddings(
            model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        )
    return _embeddings


def embed_text(text: str) -> list[float]:
    """단일 텍스트를 임베딩 벡터로 변환합니다."""
    return get_embeddings().embed_query(text)
