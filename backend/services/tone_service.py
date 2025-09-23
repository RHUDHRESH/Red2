from __future__ import annotations

from typing import Literal
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


Tone = Literal["friendly", "professional", "playful", "witty", "empathetic", "urgent", "authoritative"]


class ToneService:
    """Rewrite text to a requested tone and length."""

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def rewrite(self, text: str, *, tone: Tone = "friendly", length: Literal["short", "medium", "long"] = "short") -> str:
        if not text:
            return ""
        target_len = {"short": "~1-2 sentences", "medium": "~3-5 sentences", "long": "a short paragraph"}[length]
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a skilled copy editor. Rewrite the text to the requested tone and length. Return ONLY the rewritten text."),
            ("human", "Tone: {tone}\nLength: {length}\nText:\n{text}")
        ])
        chain = prompt | self._llm
        res = await chain.ainvoke({"tone": tone, "length": target_len, "text": text})
        return res.content.strip()

