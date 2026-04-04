from __future__ import annotations

import hashlib
import logging
from typing import Callable

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


# ── 경량 인메모리 벡터스토어 (chromadb 대체) ──────────────────────────────────


class _VectorStore:
    """numpy 코사인 유사도 기반 인메모리 벡터스토어."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._docs: list[str] = []
        self._metas: list[dict] = []
        self._embeddings: list[np.ndarray] = []

    def count(self) -> int:
        return len(self._ids)

    def upsert(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        existing = set(self._ids)
        for i, id_ in enumerate(ids):
            if id_ not in existing:
                self._ids.append(id_)
                self._docs.append(documents[i])
                self._metas.append(metadatas[i])
                self._embeddings.append(np.array(embeddings[i], dtype=np.float32))
                existing.add(id_)

    def query(self, query_embedding: list[float], n_results: int) -> dict:
        if not self._ids:
            return {"documents": [[]], "metadatas": [[]]}

        q = np.array(query_embedding, dtype=np.float32)
        matrix = np.stack(self._embeddings)           # (N, D)
        norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(q) + 1e-10
        scores = matrix @ q / norms

        top_k = min(n_results, len(scores))
        top_idx = np.argsort(scores)[::-1][:top_k]

        return {
            "documents": [[self._docs[i] for i in top_idx]],
            "metadatas": [[self._metas[i] for i in top_idx]],
        }

    def clear(self) -> None:
        self.__init__()


# ── 컬렉션 레지스트리 ─────────────────────────────────────────────────────────

_stores: dict[str, _VectorStore] = {}
_COLLECTION_NAMES = ["field_news", "economy_news"]


def _get_store(collection_name: str) -> _VectorStore:
    if collection_name not in _stores:
        _stores[collection_name] = _VectorStore()
    return _stores[collection_name]


def reset_client() -> None:
    """버튼 클릭 시 호출 — 모든 컬렉션 데이터를 초기화합니다."""
    for name in _COLLECTION_NAMES:
        if name in _stores:
            _stores[name].clear()
    logger.info("벡터스토어 초기화 완료")


# ── 공개 API ──────────────────────────────────────────────────────────────────


def upsert_articles(
    articles_data: list[dict],
    collection_name: str,
    embed_fn: Callable[[str], list[float]],
) -> int:
    """기사 목록을 청크 분할 후 벡터스토어에 저장합니다. 반환값: 저장된 청크 수"""
    store = _get_store(collection_name)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )

    ids, docs, metas, embeds = [], [], [], []

    for article in articles_data:
        text = (
            article.get("summary")
            or article.get("content")
            or article.get("title")
            or ""
        )
        if not text.strip():
            continue

        for i, chunk in enumerate(splitter.split_text(text)):
            chunk_id = hashlib.md5(
                f"{article.get('url', '')}_{i}".encode()
            ).hexdigest()
            ids.append(chunk_id)
            docs.append(chunk)
            metas.append(
                {
                    "url": article.get("url", ""),
                    "title": article.get("title", ""),
                    "source": article.get("source", ""),
                    "published_date": article.get("published_date") or "",
                }
            )
            embeds.append(embed_fn(chunk))

    if ids:
        store.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
        logger.info("[%s] upsert %d chunks", collection_name, len(ids))

    return len(ids)


def query_collection(
    query: str,
    collection_name: str,
    k: int,
    embed_fn: Callable[[str], list[float]],
) -> list[dict]:
    """벡터스토어에서 코사인 유사도 Top-K 청크를 검색합니다."""
    store = _get_store(collection_name)
    if store.count() == 0:
        logger.warning("[%s] 벡터스토어 비어있음", collection_name)
        return []

    results = store.query(embed_fn(query), n_results=min(k, store.count()))

    return [
        {
            "content": doc,
            "url": meta.get("url", ""),
            "title": meta.get("title", ""),
            "source": meta.get("source", ""),
        }
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]
