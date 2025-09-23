from pydantic import BaseModel, Field
from typing import Literal
from .positioning_schemas import PositioningOptionCard

class Objection(BaseModel):
    """
    Represents a single objection from a user about a positioning option.
    """
    text: str = Field(..., description="The user's verbatim objection.")
    type: Literal[
        "price", "proof", "relevance", "taboo", "complexity", "competitor", "compliance", "other"
    ] = Field(description="The classified type of the objection.")
    severity: Literal["critical", "minor"] = Field(description="The assessed severity of the objection.")

class ObjectionHandlingRequest(BaseModel):
    """
    The data sent from the frontend when a user raises an objection.
    """
    option_card: PositioningOptionCard = Field(description="The full positioning card the user is objecting to.")
    objection_text: str = Field(description="The user's raw feedback or objection.")

class ObjectionHandlingResponse(BaseModel):
    """
    The response from the agent, containing either a revised card or a clarifying question.
    """
    status: Literal["revised", "clarification_needed", "locked", "failed"]
    revised_card: PositioningOptionCard | None = None
    clarification_question: str | None = None
    message: str
