import logging
from typing import List, Dict, Optional

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from agents.utils.toolkit import bind_llm_with_tools

from services.registry import get_services
from schemas.dynamic_intake_schemas import (
    IntakeHints,
    PersonaProfile,
    PersonaLabel,
    DynamicTurnResponse,
)
from agents.permission_ladder_agent import build_permission_ladder
from schemas.permission_ladder_schemas import PermissionLadderRequest


logger = logging.getLogger(__name__)


# Gate 0: Disarming six questions (plus optional location)
GATE_A_REQUIRED_SLOTS = [
    "story_trigger",
    "one_line_offer",
    "price_band",
    "capacity_limit",
    "proof_link",
    "budget_cap_kill",
]
GATE_A_ALL_SLOTS = [*GATE_A_REQUIRED_SLOTS, "location"]

QUESTION_LIBRARIES: Dict[PersonaLabel, Dict[str, str]] = {
    "technical_founder": {
        "problem_validation": "Have you validated the problem with real users? What's your strongest signal?",
        "distribution": "How are you planning to reach your first 100 customers?",
        "pricing_model": "What's your current pricing hypothesis and why?",
        "alternatives": "What are users doing today instead of using your product?",
        "constraints": "Any legal, compliance, or operational constraints we must respect?",
    },
    "operator_founder": {
        "offline_traction": "What offline traction or word-of-mouth have you observed so far (orders/day, repeat %, footfall)?",
        "capacity_ops": "What capacity/ops constraints should shape the strategy (staffing, delivery radius, prep time)?",
        "local_advantages": "What location-specific strengths do you have (proximity, supplier ties, community)?",
        "seasonality": "Any seasonality or peak windows we should exploit?",
        "guardrails": "Any hard guardrails like taboos, price floors, or tone constraints?",
    },
    "marketer": {
        "kpis": "What's the single most important metric for this quarter?",
        "budget": "What budget and channels have you tried, and results so far?",
        "icp": "Describe your ICP crisply (role, context, pain, trigger).",
        "proof": "What proof or assets already exist (case studies, testimonials, metrics)?",
        "risks": "Any compliance or brand risks to avoid?",
    },
    "brick_mortar_owner": {
        "footfall": "What does typical daily/weekly footfall look like? Peak hours?",
        "local_partnerships": "Any nearby institutions or partners we can tap (colleges, offices, gyms)?",
        "menu_economics": "What are your hero products and their margins?",
        "promo_history": "What promotions worked or failed in the past?",
        "delivery_radius": "What delivery radius and SLAs can you reliably meet?",
    },
    "student_maker": {
        "project_scope": "What's the smallest valuable version you can deliver in 2 weeks?",
        "audience_seed": "Who are 20 people that will try this first?",
        "channels": "Which channels can you operate personally (Discord, Reddit, campus events)?",
        "evidence": "What early evidence would convince someone this is worth investing in?",
        "risks": "Any hard constraints (time, exams, budget)?",
    },
    # Gate 0: Coffee-style intake for unknown persona
    "unknown": {
        "story_trigger": "What sparked this? Give me the short origin story.",
        "one_line_offer": "In one friendly line: what do you offer, and for whom?",
        "price_band": "Roughly what’s the price band or average order value? A range is perfect.",
        "capacity_limit": "What’s your current capacity or throughput per day/week?",
        "proof_link": "Can you drop one link that proves this works (site, review, case study, deck)?",
        "budget_cap_kill": "What’s your 30-day budget cap and the ‘pull the plug’ line?",
        # Optional bonus to unlock geo features
        "location": "Bonus: where are you primarily located or serving? City/neighborhood/radius is fine.",
    },
}


class PersonaTool(BaseModel):
    persona_label: PersonaLabel = Field(description="Best-fit persona label")
    digital_footprint: str = Field(description="low|medium|high")
    confidence: float = 0.5
    notes: str = ""


class SlotChoice(BaseModel):
    slot: str
    reason: str


def _llm_fast() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


def _llm_reason() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.3)


def _history_to_str(history: List[str]) -> str:
    return "\n".join(history[-8:])


# --- Gate A extraction ---
class GateAData(BaseModel):
    story_trigger: Optional[str] = ""
    one_line_offer: Optional[str] = ""
    price_band: Optional[str] = ""
    capacity_limit: Optional[str] = ""
    proof_link: Optional[str] = ""
    budget_cap_kill: Optional[str] = ""
    location: Optional[str] = ""


async def extract_gate_a(history: List[str]) -> GateAData:
    """Extract Gate A fields from conversation history using the reasoning LLM.
    Empty strings mean 'not found'.
    """
    tool = bind_llm_with_tools(_llm_reason(), ["extract_keywords", "summarize_text"]).with_structured_output(GateAData)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a careful extractor. From the dialogue, extract concise answers for the provided fields."
            " If a field is not clearly answered, leave it empty. Do not hallucinate or infer numbers."
        ),
        ("human", "Recent conversation (latest last):\n{history}\n\nReturn fields: story_trigger, one_line_offer, price_band, capacity_limit, proof_link, budget_cap_kill, location."),
    ])
    chain = prompt | tool
    try:
        res = await chain.ainvoke({"history": _history_to_str(history)})
        return res
    except Exception:
        return GateAData()


def _invert_unknown_map() -> Dict[str, str]:
    """Map question text → slot for the unknown persona library."""
    inv: Dict[str, str] = {}
    for k, v in QUESTION_LIBRARIES.get("unknown", {}).items():
        inv[v] = k
    return inv


def _last_asked_slot(history: List[str]) -> Optional[str]:
    inv = _invert_unknown_map()
    for msg in reversed(history):
        if msg in inv:
            return inv[msg]
    return None


def _looks_like_refusal(text: str) -> bool:
    t = (text or "").lower()
    patterns = [
        "prefer not", "can't share", "cannot share", "don't want", "dont want",
        "not comfortable", "rather not", "n/a", "unknown", "no idea", "no clue",
        "later", "skip", "pass",
    ]
    return any(p in t for p in patterns)


def _gate_a_missing(captured: GateAData) -> List[str]:
    def _empty(v: Optional[str]) -> bool:
        return not (v and v.strip())
    missing: List[str] = []
    for slot in GATE_A_REQUIRED_SLOTS:
        if _empty(getattr(captured, slot, "")):
            missing.append(slot)
    return missing


async def classify_persona(hints: IntakeHints, history: List[str]) -> PersonaProfile:
    tool = bind_llm_with_tools(_llm_fast(), ["web_search", "extract_keywords"]).with_structured_output(PersonaTool)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a precise intake classifier. Based on conversation and optional hints, pick the persona and digital footprint quality."
            " Return only grounded judgments; if unclear, choose 'unknown' with low confidence.",
        ),
        (
            "human",
            "Conversation (recent):\n{history}\n\n"
            "Hints (JSON): name={name}, company={company}, website={website}, linkedin={linkedin}, twitter={twitter}, location={location}",
        ),
    ])
    chain = prompt | tool
    res = await chain.ainvoke(
        {
            "history": _history_to_str(history),
            "name": hints.name or "",
            "company": hints.company or "",
            "website": hints.website or "",
            "linkedin": hints.linkedin_url or "",
            "twitter": hints.twitter_handle or "",
            "location": hints.location or "",
        }
    )
    df = res.digital_footprint.lower().strip()
    if df not in ("low", "medium", "high"):
        df = "medium"
    return PersonaProfile(
        persona_label=res.persona_label,
        digital_footprint=df,
        confidence=res.confidence,
        notes=res.notes,
    )


def compute_missing_slots(persona: PersonaLabel, history: List[str]) -> List[str]:
    lib = QUESTION_LIBRARIES.get(persona, QUESTION_LIBRARIES["unknown"])  # type: ignore[index]
    missing: List[str] = []
    joined = "\n".join(history)
    for slot, question in lib.items():
        if question not in joined:
            missing.append(slot)
    return missing


async def choose_next_slot(persona: PersonaLabel, missing_slots: List[str], history: List[str]) -> str:
    if not missing_slots:
        return ""
    # For the unknown persona (Gate 0), keep the flow crisp and deterministic
    if persona == "unknown":
        return missing_slots[0]
    tool = bind_llm_with_tools(_llm_reason(), ["extract_keywords"]).with_structured_output(SlotChoice)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Select the single next slot to ask to maximize information gain. Choose only from the provided list.",
            ),
            ("human", "Persona: {persona}\nMissing slots: {slots}\nRecent conversation:\n{history}"),
        ]
    )
    chain = prompt | tool
    res = await chain.ainvoke(
        {
            "persona": persona,
            "slots": ", ".join(missing_slots),
            "history": _history_to_str(history),
        }
    )
    return res.slot if res.slot in missing_slots else missing_slots[0]


async def run_dynamic_intake_turn(
    hints: dict, history: List[str], user_message: str | None
) -> DynamicTurnResponse:
    """Run one dynamic intake turn: classify persona, pick next question, or conclude with summary."""
    hints_model = IntakeHints(**(hints or {}))
    # Append the last message to history if provided
    if user_message:
        history = [*history, user_message]

    # Persona classification with safe fallback if LLM unavailable
    try:
        persona = await classify_persona(hints_model, history)
    except Exception as e:
        logger.warning(f"[intake] classify fallback due to error: {e}")
        persona = PersonaProfile(persona_label="unknown", digital_footprint="medium", confidence=0.0, notes="offline fallback")
    # Gate A: always extract for unknown persona; for others, use original heuristic
    captured_gate_a = await extract_gate_a(history)
    missing = (
        _gate_a_missing(captured_gate_a)
        if persona.persona_label == "unknown"
        else compute_missing_slots(persona.persona_label, history)
    )

    if not missing:
        # Summarize and conclude
        # Try LLM summary, fallback to simple stitched text
        try:
            summary = await get_services().summarizer.summarize("\n".join(history), mode="detailed")
        except Exception as e:
            logger.warning(f"[intake] summarize fallback due to error: {e}")
            summary = "\n\n".join(history[-10:])
        events = ["Intake.A.ready"]
        return DynamicTurnResponse(
            persona=persona,
            ai_response=(
                "Amazing — I’ve got the essentials. Here’s what I captured; next we can kick off research and position options."
            ),
            missing_slots=[],
            done=True,
            summary=summary,
            events=events,
            captured={k: (getattr(captured_gate_a, k) or "") for k in GATE_A_ALL_SLOTS},
        )

    # Choose next slot with safe fallback
    try:
        next_slot = await choose_next_slot(persona.persona_label, missing, history)
    except Exception as e:
        logger.warning(f"[intake] choose slot fallback due to error: {e}")
        next_slot = missing[0] if missing else ""

    # Handle polite refusal for sensitive numeric topics by offering ranges
    ladder_text: Optional[str] = None
    last_slot = _last_asked_slot(history)
    if last_slot in {"price_band", "capacity_limit", "budget_cap_kill"} and _looks_like_refusal(user_message or ""):
        try:
            # Build a tiny ladder and craft a friendly nudge (not used further here)
            _ = build_permission_ladder(PermissionLadderRequest(story_assets=[], lead_magnet_angle=""))
        except Exception:
            pass
        ladder_text = (
            "No worries — we can work with ranges. Would you be comfortable picking one of these?\n"
            "• Low (conservative)  • Medium (typical)  • High (ambitious)\n"
            "If you’d like, say ‘set default’ and I’ll mark a safe midpoint and flag it as an assumption."
        )

    question = QUESTION_LIBRARIES.get(persona.persona_label, QUESTION_LIBRARIES["unknown"]).get(
        next_slot
    )  # type: ignore[index]
    if not question:
        question = QUESTION_LIBRARIES["unknown"][list(QUESTION_LIBRARIES["unknown"].keys())[0]]

    ai_text = ladder_text or question

    return DynamicTurnResponse(
        persona=persona,
        ai_response=ai_text,
        missing_slots=[s for s in missing if s != next_slot],
        done=False,
        summary=None,
        events=[],
        captured={k: (getattr(captured_gate_a, k) or "") for k in GATE_A_ALL_SLOTS},
    )
