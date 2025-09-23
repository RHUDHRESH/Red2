import math
from typing import List, Literal

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.chat_models import ChatOllama

from services.registry import get_services
from schemas.objective_router_schemas import (
    ObjectiveRouterRequest,
    ObjectiveRouterResponse,
    RouterClassifications,
    ADAPTPlan,
    AlignOut, WOOP,
    DiagnoseOut,
    ArchitectOut,
    PilotOut,
    TrackOut, TrackTargets,
)


def _fast() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model="gemma3:1b", temperature=0.0)


def _reason() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model="gemma3:4b", temperature=0.2)


CANON_MAP = {
    "awareness": "Awareness",
    "reach": "Awareness",
    "acquisition": "Acquisition",
    "signup": "Acquisition",
    "activation": "Activation",
    "onboarding": "Activation",
    "revenue": "Revenue",
    "sales": "Revenue",
    "retention": "Retention",
    "churn": "Retention",
    "referral": "Referral",
    "efficiency": "Efficiency",
    "satisfaction": "Satisfaction",
}


def canonicalize_objective(text: str) -> Literal[tuple(CANON_MAP.values())]:  # type: ignore
    t = (text or "").lower()
    for k, v in CANON_MAP.items():
        if k in t:
            return v  # type: ignore
    return "Activation"  # default conservative


def pick_game(business_type: str) -> Literal["Attention", "Transaction", "Productivity"]:
    bt = business_type.lower()
    if any(x in bt for x in ["ecommerce", "marketplace", "fintech", "local"]):
        return "Transaction"
    if any(x in bt for x in ["content", "media"]):
        return "Attention"
    return "Productivity"


def select_north_star(game: str) -> str:
    if game == "Attention":
        return "Weekly engaged minutes per user"
    if game == "Transaction":
        return "Transactions per user per month"
    return "Tasks completed per user per week"


async def classify_orientation(icp_segment: str, provided: str | None) -> Literal["promotion", "prevention"]:
    if provided in ("promotion", "prevention"):
        return provided  # type: ignore
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Classify regulatory focus as 'promotion' or 'prevention' based on segment text."),
        ("human", "Segment: {seg}")
    ])
    out = (prompt | _fast()).invoke({"seg": icp_segment}).content.strip().lower()
    return "promotion" if "promotion" in out else "prevention"


def diagnose_comb(canonical: str) -> List[Literal["Capability", "Opportunity", "Motivation"]]:
    # Heuristics by objective
    if canonical in ("Activation", "Retention", "Productivity"):
        return ["Capability", "Opportunity"]
    if canonical in ("Awareness", "Acquisition", "Referral"):
        return ["Motivation"]
    return ["Opportunity"]


def pick_fogg_prompt(comb: List[str]) -> Literal["Spark", "Signal", "Facilitator"]:
    if "Motivation" in comb:
        return "Spark"
    if "Capability" in comb or "Opportunity" in comb:
        return "Facilitator"
    return "Signal"


def woopize(canonical: str, objective_text: str) -> WOOP:
    wish = objective_text
    outcome = f"Achieve {canonical} lift"
    obstacle = "Users lack time or guidance"
    plan = "If user stalls before aha, then trigger guide + message"
    return WOOP(wish=wish, outcome=outcome, obstacle=obstacle, plan_if_then=plan)


def default_metrics(canonical: str, north_star: str) -> ArchitectOut:
    if canonical == "Awareness":
        return ArchitectOut(north_star_inputs=["brand_search_lift", "28_day_retention_seed"], HEART=["Happiness", "Engagement"])
    if canonical == "Acquisition":
        return ArchitectOut(north_star_inputs=["cac_to_signup", "cac_to_activated"], HEART=["Adoption"])
    if canonical == "Activation":
        return ArchitectOut(north_star_inputs=["time_to_value_minutes", "checklist_completion_rate", "day2_revisit_rate"], HEART=["Adoption", "Task success", "Retention"])
    if canonical == "Revenue":
        return ArchitectOut(north_star_inputs=["arpu", "g_mv", "buyer_conversion"], HEART=["Engagement"])
    if canonical == "Retention":
        return ArchitectOut(north_star_inputs=["n_day_retention", "churn_rate"], HEART=["Retention"])
    if canonical == "Referral":
        return ArchitectOut(north_star_inputs=["invites_per_user", "invite_acceptance"], HEART=["Engagement"])
    if canonical == "Efficiency":
        return ArchitectOut(north_star_inputs=["cac", "payback_months", "ltv_to_cac"], HEART=[])
    if canonical == "Satisfaction":
        return ArchitectOut(north_star_inputs=["nps", "csat"], HEART=["Happiness"])
    return ArchitectOut(north_star_inputs=[], HEART=[])


def barbell_portfolio() -> PilotOut:
    core = ["shorten onboarding", "auto sample data", "checklist", "clear value story"]
    spikes = ["AI auto-setup", "template marketplace"]
    risks = ["underpowered A/B", "segment mismatch", "prompt fatigue"]
    return PilotOut(barbell={"core": core, "spikes": spikes}, premortem_top_risks=risks)


def targets_and_forecasts(north_star_key: str) -> TrackOut:
    # Minimal deterministic example; replace with real baselines
    ns_key = {
        "Weekly engaged minutes per user": "ns_weekly_minutes",
        "Transactions per user per month": "ns_tx_per_user",
        "Tasks completed per user per week": "ns_tasks_per_user",
    }.get(north_star_key, "north_star")
    t = TrackOut(targets={}, forecast_eval="Brier", cadence="OODA two-week loop")
    t.targets[ns_key] = TrackTargets(baseline=1.0, target=1.6, p50=1.5, p80=1.7)
    return t


async def run_objective_router(req_dict: dict) -> dict:
    req = ObjectiveRouterRequest(**req_dict)
    canonical = canonicalize_objective(req.objective)
    game = pick_game(req.business_type)
    north_star = select_north_star(game)
    orientation = await classify_orientation(req.icp.segment, req.icp.orientation)
    comb_gaps = diagnose_comb(canonical)
    fogg = pick_fogg_prompt(comb_gaps)

    plan = ADAPTPlan(
        align=AlignOut(goal_statement=req.objective, woop=woopize(canonical, req.objective)),
        diagnose=DiagnoseOut(comb_gaps=comb_gaps, fogg_prompt=fogg),
        architect=default_metrics(canonical, north_star),
        pilot=barbell_portfolio(),
        track=targets_and_forecasts(north_star),
    )

    resp = ObjectiveRouterResponse(objective_router_v1={
        "inputs": {
            "objective": req.objective,
            "icp": {"segment": req.icp.segment, "orientation": orientation},
            "business_type": req.business_type,
        },
        "classifications": {
            "canonical_objective": canonical,
            "engagement_game": game,
            "north_star": north_star,
        },
        "ADAPT_plan": plan.model_dump(),
    })
    return resp.model_dump()

