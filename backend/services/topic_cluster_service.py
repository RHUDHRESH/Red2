from __future__ import annotations

from typing import List, Dict, Any

from .embedding_service import EmbeddingService


class TopicClusterService:
    """Clusters short texts (e.g., keywords, headlines) by cosine similarity.

    Greedy assignment with centroid updates. Suitable for small lists (< 200).
    """

    def __init__(self, embedder: EmbeddingService) -> None:
        self._embedder = embedder

    async def cluster(self, texts: List[str], *, threshold: float = 0.78) -> List[Dict[str, Any]]:
        if not texts:
            return []
        vecs = await self._embedder.embed(texts)
        clusters: List[Dict[str, Any]] = []

        def cosine(a: List[float], b: List[float]) -> float:
            # Inline to avoid extra imports
            dot = sum(x * y for x, y in zip(a, b))
            na = (sum(x * x for x in a) ** 0.5) or 1e-9
            nb = (sum(y * y for y in b) ** 0.5) or 1e-9
            return dot / (na * nb)

        for i, (t, v) in enumerate(zip(texts, vecs)):
            if not clusters:
                clusters.append({"centroid": v[:], "items": [t]})
                continue
            # Find best cluster
            best_idx, best_sim = -1, -1.0
            for idx, c in enumerate(clusters):
                sim = cosine(v, c["centroid"])
                if sim > best_sim:
                    best_idx, best_sim = idx, sim
            if best_sim >= threshold:
                c = clusters[best_idx]
                c["items"].append(t)
                # Update centroid (simple mean)
                n = len(c["items"])  # after append
                c["centroid"] = [((old * (n - 1)) + val) / n for old, val in zip(c["centroid"], v)]
            else:
                clusters.append({"centroid": v[:], "items": [t]})

        # Remove centroids from output
        return [{"items": c["items"]} for c in clusters]

