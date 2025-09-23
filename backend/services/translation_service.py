from __future__ import annotations

from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


class TranslationService:
    """LLM-based translation helper.

    Keeps output clean (no explanations). Preserves numbers and formatting when possible.
    """

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def translate(self, text: str, *, target_lang: str = "en", source_lang: str | None = None) -> str:
        if not text:
            return ""
        sys = (
            "You are a professional translator. Translate the user's text into the target language. "
            "Preserve meaning, tone, numbers, currency, and proper nouns. Return ONLY the translated text."
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys),
            ("human", "Target language: {t}\n" + ("Source language: {s}\n" if source_lang else "") + "Text:\n{text}")
        ])
        chain = prompt | self._llm
        res = await chain.ainvoke({"t": target_lang, "s": source_lang or "", "text": text})
        return res.content.strip()

