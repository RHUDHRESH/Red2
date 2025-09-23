from __future__ import annotations

from typing import List

from schemas.neurofoundry_schemas import (
    ADAPT20,
    FramePlan,
    BehaviorPlan,
    AssetDNA,
    MemeticRails,
    StyleMatch,
    EarnedEffort,
    Pratfall,
    CompileRequest,
    CompileResponse,
    EmailDraft,
    SocialDraft,
    LandingOutline,
    Rubric,
)


def normalize_adapt(raw: dict) -> ADAPT20:
    # Simple coercion via Pydantic; callers should pass fields per spec
    return ADAPT20(**raw)


def select_frame(adapt: ADAPT20) -> FramePlan:
    # Heuristic: if awareness low, lean on social proof; if high urgency, scarcity
    aw = adapt.audience.awareness
    urgency = adapt.timing.urgency
    primary = "social_proof" if aw in ("problem", "solution") else "authority"
    if urgency == "high":
        primary = "scarcity"
    return FramePlan(primary=primary, pre_suasion="prime relevance with shared identity", guardrail="ethical, truthful, no false scarcity")


def map_behavior(adapt: ADAPT20) -> BehaviorPlan:
    # Minimal mapping rules
    prompt = "facilitator"
    if adapt.timing.cadence == "drip":
        prompt = "signal"
    bmap = {"prompt": prompt, "ability_lowering": "preset"}
    comb = {
        "capability": "give a one-tap path",
        "opportunity": "deliver at best time window",
        "motivation": "tie to immediate micro-win",
    }
    east = {
        "easy": "single clear action",
        "attractive": "show one vivid benefit",
        "social": "add one proof cue",
        "timely": "send inside chosen window",
    }
    return BehaviorPlan.model_validate({"b_map": bmap, "com_b": comb, "east": east})


def build_dna(adapt: ADAPT20) -> AssetDNA:
    claim = adapt.desired_outcome.business or "A concrete win this month"
    warrant = "Because our evidence directly demonstrates this outcome for peers like you"
    cta = {"action": "Book a demo", "time_cost": "<2 min", "incentive": "starter plan"}
    return AssetDNA(
        claim=claim,
        evidence=adapt.proof_assets,
        warrant=warrant,
        risks=adapt.risks,
        counters=["transparent pricing", "guided onboarding"],
        cta=cta,
    )


def memetic_engine() -> MemeticRails:
    return MemeticRails(
        fluency_rules=["short sentences", "concrete nouns", "low jargon"],
        curiosity_seeds=["pose a question the paragraph must close"],
        open_loops=["tease the next step in P.S."],
        isolation_pop="one phrasing pattern-break per fold",
        peak_end={"peak": "vivid micro-win", "end": "crisp closing line"},
    )


def style_match(adapt: ADAPT20) -> StyleMatch:
    # Stubbed LSM score to a mid value
    return StyleMatch(lsm_score=78, notes="mirrors target function words and cadence")


def earned_effort_step() -> EarnedEffort:
    return EarnedEffort(ikea_step="Pick your channel", fallback="Default to email")


def pratfall_switch() -> Pratfall:
    return Pratfall(pratfall_note="One humanizing imperfection in non-critical claim")


def _score_rubric(style: StyleMatch) -> Rubric:
    return Rubric(
        map_fit=84,
        com_b_coverage=80,
        east_compliance=82,
        fluency_score=86,
        lsm_score=style.lsm_score,
        distinctiveness_index=72,
        peak_end_delta=79,
        prospect_alignment=83,
        ikea_gain_risk="safe",
        pratfall_sanity="safe",
        red_flags=[],
    )


def compile_asset(req: CompileRequest) -> CompileResponse:
    rails = memetic_engine()
    style = style_match(req.adapt)
    ikea = earned_effort_step()
    pr = pratfall_switch()

    if req.channel == "email":
        draft = EmailDraft(
            subject="{outcome} in 7 days".format(outcome=req.adapt.desired_outcome.business or "A quick win"),
            line1="{frame} signal for {segment}".format(frame=req.frame.primary.replace("_", " "), segment=req.adapt.audience.segment or "your peers"),
            body=f"{req.dna.claim}. One proof: {req.dna.evidence[0].value if req.dna.evidence else 'see case'}. Why it matters: {req.dna.warrant}. CTA: {req.dna.cta.get('action','Act now')} ({req.dna.cta.get('time_cost','<2 min')}).",
            ps="Tomorrow: how we pre-fill your intake (open loop)",
        ).model_dump()
    elif req.channel == "social":
        draft = SocialDraft(
            hook="Pattern-break: {enemy} dies".format(enemy=req.frame.primary),
            body=f"{req.dna.claim}. Proof and warrant inline.",
            close="Micro-outcome this week. Save for later.",
        ).model_dump()
    else:
        draft = LandingOutline(
            hero=f"Avoid {req.adapt.risks[0] if req.adapt.risks else 'lost weeks'} + micro-win now",
            proof_wall=[p.value for p in req.dna.evidence[:3]],
            how_it_works=["3 steps tied to ability lowering"],
            cta_rail="Visible progress meter to exploit goal-gradient",
        ).model_dump()

    rubric = _score_rubric(style)
    return CompileResponse(
        channel=req.channel,
        draft=draft,
        rails=rails,
        style=style,
        earned_effort=ikea,
        pratfall=pr,
        rubric=rubric,
    )

