from __future__ import annotations

import logging
from collections import Counter
from typing import List

from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)


STOPWORDS = set(
    "the a an and or for of to in on with without at by from this that these those is are was were be being been as it its their your our his her you we they".split()
)


class KeywordService:
    """Extracts keywords/topics via LLM, falls back to naive frequency."""

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def extract(self, text: str, *, top_k: int = 12) -> List[str]:
        if not text:
            return []
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", "Extract up to {k} key topics/keywords, comma-separated. Lowercase, no duplicates."),
                ("human", "Text:\n{text}")
            ])
            chain = prompt | self._llm
            res = await chain.ainvoke({"text": text[:2000], "k": top_k})
            raw = res.content.strip().lower()
            parts = [p.strip() for p in raw.replace(";", ",").split(",")]
            seen = set(); out = []
            for p in parts:
                if not p or p in seen:
                    continue
                seen.add(p)
                out.append(p)
            return out[:top_k]
        except Exception as e:
            logger.warning(f"[keywords] LLM failed, using fallback: {e}")
            words = [w.strip(".,!?:;()[]{}'\" ").lower() for w in text.split()]
            words = [w for w in words if w and w not in STOPWORDS and w.isalpha() and len(w) > 2]
            common = Counter(words).most_common(top_k)
            return [w for w, _ in common]

