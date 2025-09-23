from __future__ import annotations

import random
import time
from typing import List

from services.registry import get_services
from services.pdf_writer_service import make_simple_pdf_base64
from schemas.ops_schemas import (
    MicroPlayRequest,
    MicroPlayResponse,
    MicroPlay,
    ICEScore,
    SourceRef,
)


GBP_HELP = "Google Help"
THE_VERGE = "The Verge"
EATER = "Eater"
BON_APPETIT = "Bon Appétit"
TIME_MAG = "TIME"
YELP = "Yelp Blog"


async def _gather_sources() -> List[SourceRef]:
    rss = get_services().rss
    out: List[SourceRef] = []
    feeds = [
        (EATER, "https://www.eater.com/rss/index.xml"),
        (BON_APPETIT, "https://www.bonappetit.com/feed/rss"),
        (TIME_MAG, "https://time.com/feed/"),
        (THE_VERGE, "https://www.theverge.com/rss/index.xml"),
        (YELP, "https://blog.yelp.com/feed/"),
    ]
    for name, url in feeds:
        try:
            items = await rss.parse(url)
            if items:
                top = items[0]
                out.append(SourceRef(title=top.title, url=top.url, source=name))
        except Exception:
            continue
    # GBP help (no RSS) — add a generic reference
    out.append(SourceRef(title="Business Profile Help Center", url="https://support.google.com/business", source=GBP_HELP))
    return out


def _rand_codes(n: int = 2) -> List[str]:
    return [f"AB{random.randint(100,999)}" for _ in range(n)]


async def run_restaurant_micro_strategy(req: MicroPlayRequest) -> MicroPlayResponse:
    # Guardrail: suppress if baseline CX broken
    if req.baseline_ok is False or (req.avg_rating is not None and req.avg_rating < 3.5):
        return MicroPlayResponse(
            suppressed=True,
            reason=(
                "Delight suppressed: fix baseline CX first. Evidence shows delight multiplies satisfaction,"
                " not replaces it (McKinsey). Address service reliability, speed, and errors before stunts."
            ),
            plays=[],
            kpis=[
                "Return visit rate",
                "Check-in rate",
                "GBP actions",
                "Yelp review velocity",
                "Cost per repeat",
            ],
        )

    sources = await _gather_sources()
    now = int(time.time())

    # Construct exemplar micro-plays with ICE scoring
    plays: List[MicroPlay] = []

    plays.append(
        MicroPlay(
            id="mp_secret_bite",
            channel="FOH",
            title="Handwritten thank-you + rotating midweek ‘Secret Bite’",
            description=(
                "On first order, include a handwritten note with a QR to a midweek-only ‘secret bite’."
                " Rotate monthly to keep novelty."
            ),
            rationale="Small personal touches drive delight and word-of-mouth; exclusivity increases redemption.",
            sources=[s for s in sources if s.source in (BON_APPETIT,)],
            ice=ICEScore(impact=8.0, confidence=7.0, ease=6.0),
            kpis=["Return visit rate", "Midweek redemptions", "Review lift"],
            ab_variant_codes=_rand_codes(),
            sop_pdf_base64=make_simple_pdf_base64(
                "SOP: Secret Bite Thank-You",
                (
                    "Goal: Increase repeat visits via small-delight + exclusivity.\n\n"
                    "Steps:\n"
                    "1) FOH keeps a stack of pre-printed cards with QR (A/B code variant).\n"
                    "2) Add handwritten name + 1-liner thanks; attach to first-order bags.\n"
                    "3) Secret bite valid Tue–Thu only; rotate monthly.\n\n"
                    "Measurement: midweek redemptions, repeat rate, reviews mentioning ‘note’."
                ),
            ),
        )
    )

    plays.append(
        MicroPlay(
            id="mp_birthday_comp_gbp",
            channel="UGC",
            title="Automated birthday comp via GBP ‘What’s happening this week’",
            description=(
                "Publish a weekly Business Profile post advertising a birthday comp flow; use in-house cue cards"
                " so staff can trigger the flow consistently."
            ),
            rationale="Business Profile posts capture local intent; birthdays are a repeatable delight moment.",
            sources=[s for s in sources if s.source in (THE_VERGE, GBP_HELP)],
            ice=ICEScore(impact=7.0, confidence=6.5, ease=6.0),
            kpis=["GBP actions", "Birthday redemptions", "Repeat rate"],
            ab_variant_codes=_rand_codes(),
            sop_pdf_base64=make_simple_pdf_base64(
                "SOP: Birthday Comp via GBP",
                (
                    "Goal: Increase GBP actions + repeat via birthday comp.\n\n"
                    "Steps:\n"
                    "1) Draft weekly GBP post with photo; include ‘Show this post’ CTA.\n"
                    "2) FOH cue cards outline verification + comp limits.\n"
                    "3) Track via tally at POS + QR code variant."
                ),
            ),
        )
    )

    plays.append(
        MicroPlay(
            id="mp_yelp_checkin_incentive",
            channel="Delivery",
            title="Yelp check‑in incentive that rotates monthly",
            description="Offer small rotating perk on Yelp check‑in; avoid fatigue via monthly swap informed by page analytics.",
            rationale="Dynamic offers preserve novelty; Yelp check‑ins correlate with local demand.",
            sources=[s for s in sources if s.source in (YELP,)],
            ice=ICEScore(impact=6.5, confidence=6.0, ease=6.5),
            kpis=["Check-in rate", "Offer redemption", "Review velocity"],
            ab_variant_codes=_rand_codes(),
            sop_pdf_base64=make_simple_pdf_base64(
                "SOP: Yelp Check‑in Incentive",
                (
                    "Goal: Lift check-ins without offer fatigue.\n\n"
                    "Steps:\n"
                    "1) Configure a small perk (e.g., free dip) for check‑ins.\n"
                    "2) Rotate the perk monthly; announce via assets on Yelp.\n"
                    "3) Track with QR variants on table tents/inserts."
                ),
            ),
        )
    )

    # Trim to requested max_items
    plays = sorted(plays, key=lambda p: p.ice.score, reverse=True)[: req.max_items]

    return MicroPlayResponse(
        suppressed=False,
        reason=None,
        plays=plays,
        kpis=[
            "Return visit rate",
            "Check-in rate",
            "GBP actions",
            "Yelp review velocity",
            "Cost per repeat",
        ],
    )

