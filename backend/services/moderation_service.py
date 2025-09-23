from __future__ import annotations

import logging
from typing import List

from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


logger = logging.getLogger(__name__)


class ModerationReport(BaseModel):
    compliance_ok: bool = True
    risk_level: str = Field(default="low", description="low|medium|high")
    risky_terms: List[str] = Field(default_factory=list)
    legal_claims_detected: List[str] = Field(default_factory=list)
    notes: str = ""


class ModerationService:
    """Light compliance/moderation helper using an LLM classifier.

    Useful for creative assets, taglines, or positioning statements.
    """

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def evaluate(self, text: str) -> ModerationReport:
        try:
            tool = self._llm.with_structured_output(ModerationReport)
            prompt = ChatPromptTemplate.from_messages([
                ("system",
                 "You are a cautious compliance reviewer for marketing content in India. "
                 "Flag false/unverifiable medical/financial claims, competitor slander, impossible guarantees, or taboo topics. "
                 "Estimate risk level (low|medium|high)."),
                ("human", "Text to review:\n{text}")
            ])
            chain = prompt | tool
            res = await chain.ainvoke({"text": text})
            return res
        except Exception as e:
            logger.warning(f"[moderation] LLM failed: {e}")
            return ModerationReport(compliance_ok=True, risk_level="low", notes="LLM unavailable; passed by default")

