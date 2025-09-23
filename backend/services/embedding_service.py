from __future__ import annotations

import logging
from typing import List, Tuple
from math import sqrt

from langchain_ollama.embeddings import OllamaEmbeddings


logger = logging.getLogger(__name__)


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a)) or 1e-9
    nb = sqrt(sum(y * y for y in b)) or 1e-9
    return dot / (na * nb)


class EmbeddingService:
    """Convenience wrapper around OllamaEmbeddings with semantic search helpers."""

    def __init__(self, embeddings: OllamaEmbeddings) -> None:
        self._emb = embeddings

    async def embed(self, texts: List[str]) -> List[List[float]]:
        try:
            return await self._emb.aembed_documents(texts)
        except Exception:
            # Fallback to sync embed if async unsupported
            return self._emb.embed_documents(texts)

    async def semantic_search(self, query: str, texts: List[str], *, top_k: int = 5) -> List[Tuple[int, float]]:
        if not texts:
            return []
        qv = (await self.embed([query]))[0]
        tvs = await self.embed(texts)
        sims = [(i, _cosine(qv, tvs[i])) for i in range(len(texts))]
        sims.sort(key=lambda x: x[1], reverse=True)
        return sims[:top_k]

