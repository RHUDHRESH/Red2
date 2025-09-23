from __future__ import annotations

from typing import List
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langchain_core.prompts import ChatPromptTemplate


class Entities(BaseModel):
    people: List[str] = Field(default_factory=list)
    organizations: List[str] = Field(default_factory=list)
    brands: List[str] = Field(default_factory=list)
    products: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    dates: List[str] = Field(default_factory=list)
    amounts: List[str] = Field(default_factory=list)


class NERService:
    """Named-entity and term extractor using structured LLM output."""

    def __init__(self, llm: ChatOllama) -> None:
        self._llm = llm

    async def extract(self, text: str) -> Entities:
        tool = self._llm.with_structured_output(Entities)
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Extract entities as lists. Only include what's explicitly present. No hallucinations."),
            ("human", "Text:\n{text}")
        ])
        chain = prompt | tool
        return await chain.ainvoke({"text": text[:4000]})

