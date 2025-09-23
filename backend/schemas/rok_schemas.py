from __future__ import annotations

from typing import List, Literal
from pydantic import BaseModel, Field


class ROKInput(BaseModel):
    positioning: str
    differentiators: List[str] = Field(default_factory=list)


class Spine(BaseModel):
    enemy_6w: str
    mechanism_8w: str
    transformation_12w: str
    commanders_intent: str


class BiasLock(BaseModel):
    lock: Literal[
        "loss_aversion",
        "status_gain",
        "effort_heuristic",
        "curiosity_gap",
        "von_restorff",
        "identity",
    ]
    line: str


class StoryPrimitives(BaseModel):
    hook: str
    turn: str
    payoff: str


class WeirdDir(BaseModel):
    level: Literal["safe", "spicy", "unhinged"]
    image: str


class Taglines(BaseModel):
    benefit_blunt: str
    enemy_burn: str
    mechanism_flex: str
    status_whisper: str
    curiosity_gap: str
    number_spike: str
    rhyme_or_rhythm: str


class ROKOutput(BaseModel):
    spine: Spine
    bias_locks: List[BiasLock] = Field(default_factory=list)
    story_primitives: StoryPrimitives
    weirdness_dial: List[WeirdDir] = Field(default_factory=list)
    big_idea_sentence: str
    taglines: Taglines
    retell_score_pred: int = 4

