
from pydantic import BaseModel
from typing import List, Literal
class IntakeState(BaseModel):
    consent: bool = False; transcript: List[str] = []; facts: List[str] = []; claims: List[str] = []; missing_slots: List[str] = []; sentiment: str = "neutral"
