from __future__ import annotations

import hashlib
import logging
from typing import Callable

import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.EphemeralClient()
    return _client


_COLLECTION_NAMES = ["field_news", "economy_news"]


def reset_client() -> None:
    """버튼 클릭 시 호출 — 컬렉션만 삭제하여 데이터를 초기화합니다.

    EphemeralClient를 재생성하면 ChromaDB 내부 Rust 바인딩 해제 오류가 발생하므로
    클라이언트는 유지하고 컬렉션만 삭제합니다.
    """
    client = get_client()
    for name in _COLLECTION_NAMES:
        try:
            client.delete_collection(name)
            logger.info("ChromaDB 컬렉션 삭제: %s", name)
        except Exception:
            pass
    logger.info("ChromaDB 컬렉션 초기화 완료")


def _get_or_create_collection(collection_name: str) -> chromadb.Collection:
    client = get_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_articles(
    articles_data: list[dict],
    collection_name: str,
    embed_fn: Callable[[str], list[float]],
) -> int:
    """기사 목록을 청크 분할 후 ChromaDB에 저장합니다. 반환값: 저장된 청크 수"""
    collection = _get_or_create_collection(collection_name)
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

        chunks = splitter.split_text(text)
        for i, chunk in enumerate(chunks):
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
        collection.upsert(ids=ids, documents=docs, metadatas=metas, embeddings=embeds)
        logger.info("ChromaDB [%s] upsert %d chunks", collection_name, len(ids))

    return len(ids)


def query_collection(
    query: str,
    collection_name: str,
    k: int,
    embed_fn: Callable[[str], list[float]],
) -> list[dict]:
    """ChromaDB에서 코사인 유사도 Top-K 청크를 검색합니다."""
    collection = _get_or_create_collection(collection_name)
    total = collection.count()
    if total == 0:
        logger.warning("ChromaDB [%s] 비어있음", collection_name)
        return []

    actual_k = min(k, total)
    query_embedding = embed_fn(query)
    results = collection.query(
        query_embeddings=[query_embedding], n_results=actual_k
    )

    docs = []
    for i, doc in enumerate(results["documents"][0]):
        meta = results["metadatas"][0][i]
        docs.append(
            {
                "content": doc,
                "url": meta.get("url", ""),
                "title": meta.get("title", ""),
                "source": meta.get("source", ""),
            }
        )
    return docs
