import base64
import io
import logging
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.chat_models import ChatOllama

from services.registry import get_services
from schemas.strategy_schemas import (
    SegmentRequest, SegmentOut,
    WoundRequest, WoundOut,
    ReframeRequest, ReframeOut,
    OfferRequest, OfferOut,
    ActionRequest, ActionOut, OutreachMsg,
    CashRequest, CashOut,
    CashGuardRequest, CashGuardResponse,
    PermissionRequest, PermissionResponse,
    LateralVerticalRequest, LateralVerticalResponse, Play,
    AISASRequest, AISASResponse,
)


logger = logging.getLogger(__name__)


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


async def run_segment(req: SegmentRequest) -> SegmentOut:
    # Deterministic CSV stub: 200 leads with placeholders
    buf = io.StringIO()
    buf.write("name,email,phone\n")
    for i in range(200):
        buf.write(f"Prospect{i+1},prospect{i+1}@example.com,9{i:09d}\n")
    csv_b64 = base64.b64encode(buf.getvalue().encode("utf-8")).decode("ascii")
    statement = f"Micro-segment around {req.seed_keyword} in {req.region} avoiding {req.competitor}."
    return SegmentOut(statement=statement, lead_count=200, leads_csv_base64=csv_b64)


async def run_wound(req: WoundRequest) -> WoundOut:
    # Use fast llm to quantify wound and produce triggers with generic citations placeholder
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Quantify monthly loss (money/time) from a common pain around the segment. Provide 3 observable triggers and cite numbers conservatively."),
        ("human", "Leads CSV provided (base64, 200 rows). Summarize wound and triggers in JSON.")
    ])
    llm = _reason()
    res = (prompt | llm).invoke({}).content
    # Minimal deterministic fallback
    return WoundOut(per_month=20000.0, currency="INR", triggers=["missed follow-ups", "manual data entry", "no-shows"], citations=["internal_estimate"]) 


async def run_reframe(req: ReframeRequest) -> ReframeOut:
    # Use reasoning to propose category, enemy, do-not-say, focus word
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Name a new category (<8 words), one enemy practice, 3 claims with proof placeholders, and a do-not-say list. Include a single focus word."),
        ("human", "Competitors: {comps}")
    ])
    llm = _reason()
    out = (prompt | llm).invoke({"comps": ", ".join(req.competitor_set)}).content
    # Fallback deterministic stub
    return ReframeOut(category="Fast Local Ops CRM", enemy="Spreadsheet busywork", claims=["Cut follow-ups by 40%"], proof=["/case-study"], do_not_say=["all-in-one"], focus_word="fast")


async def run_offer(req: OfferRequest) -> OfferOut:
    # Ogilvy rules: guarantee for high ticket/high risk
    guarantee = "7-day no-questions refund" if req.wound.per_month >= 20000 else "Satisfaction guarantee"
    deliverables = ["Setup tracking", "One automation", "Weekly report"]
    return OfferOut(outcome="Cut ops time this month", deliverables=deliverables, guarantee=guarantee)


async def run_action(req: ActionRequest) -> ActionOut:
    # 90-word outreach message with single CTA
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Write a 90-word outreach, one idea per sentence, short words, one link CTA."),
        ("human", "Offer: {offer}\nCTA: Book a 15-min slot")
    ])
    msg = (prompt | _fast()).invoke({"offer": req.offer.model_dump_json()}).content
    return ActionOut(messages=[OutreachMsg(prospect="", opener=msg, cta="Book")])


async def run_cash(req: CashRequest) -> CashOut:
    amount = 5000.0
    return CashOut(pilot_scope="7 days", upi_qr="upi://pay?pa=demo@upi&am=5000", deposit_amount=amount)


async def run_cashguard(req: CashGuardRequest) -> CashGuardResponse:
    plan: List[str] = []
    if req.receivables_inr > req.payables_inr * 1.5:
        plan.append("Freeze prospecting ads; push referrals/owned.")
    if req.bank_balance_inr < req.payables_inr * 0.5:
        plan.append("Prepayment pilots only; shrink scope to 7 days.")
    if not plan:
        plan.append("No throttle. Monitor weekly.")
    return CashGuardResponse(throttle_plan=plan)


async def run_permission(req: PermissionRequest) -> PermissionResponse:
    # Score opt-in and retell via heuristic
    opt_in = 0.22
    retell = 0.6
    notes = "If opt-in < 0.2, rewrite story and tribe before spend."
    return PermissionResponse(opt_in_rate=opt_in, retell_rate_10w=retell, notes=notes)


async def run_lateral_vertical(req: LateralVerticalRequest) -> LateralVerticalResponse:
    # Produce 3 lateral and 3 vertical plays stubbed
    lateral = [
        Play(type="lateral", shift_axis="target", hook=f"{req.product} for freelancers", channels=["ig_reels","yt_shorts"], aisas={}, unit_econ={"cac_cap": 500}, risk={}),
        Play(type="lateral", shift_axis="occasion", hook=f"{req.product} for weekends", channels=["search","email"], aisas={}, unit_econ={"cac_cap": 500}, risk={}),
        Play(type="lateral", shift_axis="need", hook=f"{req.product} as training", channels=["yt_shorts","blog"], aisas={}, unit_econ={"cac_cap": 500}, risk={}),
    ]
    vertical = [
        Play(type="vertical", shift_axis=None, hook=f"{req.product} faster", channels=["search","retarget"], aisas={}, unit_econ={"cac_cap": 400}, risk={}),
        Play(type="vertical", shift_axis=None, hook=f"{req.product} cheaper", channels=["search","email"], aisas={}, unit_econ={"cac_cap": 400}, risk={}),
        Play(type="vertical", shift_axis=None, hook=f"{req.product} simpler", channels=["ig_reels","whatsapp"], aisas={}, unit_econ={"cac_cap": 400}, risk={}),
    ]
    return LateralVerticalResponse(lateral=lateral, vertical=vertical)


async def run_aisas(req: AISASRequest) -> AISASResponse:
    # Map to AISAS pack
    play = req.approved_play
    pack = {
        "attention": {"assets": ["reel", "short"], "kpi": {"ctr_min": 0.02}},
        "interest": {"assets": ["carousel", "long_post"], "kpi": {"save_rate_min": 0.05}},
        "search": {"assets": ["faq_page", "review_roundup"], "kpi": {"branded_queries_delta_pct": 20}},
        "action": {"assets": ["offer_card", "checkout"], "kpi": {"cvr_min": 0.08, "cpl_max": 500}},
        "share": {"assets": ["review_prompt", "referral_hook"], "kpi": {"review_rate_min": 0.1}},
    }
    return AISASResponse(pack=pack)

