from __future__ import annotations

import logging
from typing import Literal

from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)


class SummarizationService:
    """LLM-powered text summarizer with simple chunking.

    Keeps prompts short and consistent; callers pick brief or detailed mode.
    """

    def __init__(self, llm: ChatOllama, *, max_chunk_chars: int = 1800) -> None:
        self._llm = llm
        self._max = max_chunk_chars

    def _chunks(self, text: str):
        t = text or ""
        if len(t) <= self._max:
            yield t
            return
        i = 0
        while i < len(t):
            yield t[i : i + self._max]
            i += self._max

    async def summarize(self, text: str, *, mode: Literal["brief", "detailed"] = "brief") -> str:
        if not text:
            return ""
        tone = "3 crisp bullet points" if mode == "brief" else "a concise paragraph"
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"You are a precise summarizer. Produce {tone}. Avoid fluff."),
            ("human", "Text:\n{chunk}")
        ])
        chain = prompt | self._llm

        parts = []
        for chunk in self._chunks(text):
            try:
                res = await chain.ainvoke({"chunk": chunk})
                parts.append(res.content.strip())
            except Exception as e:
                logger.warning(f"[summarize] failed chunk: {e}")
        # Merge parts succinctly
        if not parts:
            return ""
        if mode == "brief":
            return "\n".join(parts)
        return "\n\n".join(parts)

