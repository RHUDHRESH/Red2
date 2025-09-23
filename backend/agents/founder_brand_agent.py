from __future__ import annotations

from typing import List

from schemas.founder_brand_schemas import (
    FounderBrandInput,
    FounderBrandResponse,
    FounderBrandCodex,
    BrandVoice,
    MeasurementTier,
)


def generate_codex(req: FounderBrandInput) -> FounderBrandResponse:
    positioning_core = {
        "be_first_or_new_category": req.desired_word,
        "target_audience": req.target_audience,
        "single_word_to_own": req.desired_word,
    }

    narrative_buckets = {
        "origin": ["inciting incident", "early proof"],
        "purpose": ["the villain we fight", "values we keep"],
        "method": ["your named method", "why it works"],
        "proof": ["case A", "case B"],
        "publicity": ["press link"],
        "process": ["onboarding in 3 steps"],
        "transformation": ["before/after story"],
    }

    audience_resonance_map = {
        "worldview": "People like us do things like this",
        "triggers": "fear of wasted weeks; desire for recognition",
        "watering_holes": "LinkedIn, X, SaaS Slack groups",
        "vernacular": "CAC, LTV, MRR, churn",
    }

    voice = BrandVoice(
        personality=["authoritative", "generous"],
        tone_notes=["teaching", "supporting"],
        rhythm="short openers, then grounded detail",
        vocabulary_do=["MRR", "churn", "lead velocity"],
        vocabulary_dont=["synergy", "paradigm"],
    )

    content_mapping = {
        "awareness": ["problem explainer thread", "short video"],
        "consideration": ["webinar", "guide", "case study"],
        "decision": ["demo", "testimonial wall"],
        "advocacy": ["member spotlight", "referral program"],
    }

    asymmetric_moves = [
        "Segment collapse: own a narrow use‑case",
        "Narrative jujitsu: nimble & personal vs big & slow",
        "Sacred cow: transparent productized pricing",
    ]

    measurement = {
        "tier1": MeasurementTier(metrics={"search_volume": "trend up", "reach": "unique viewers"}),
        "tier2": MeasurementTier(metrics={"engagement_rate": "(likes+comments+shares)/followers", "invites": "speaking requests"}),
        "tier3": MeasurementTier(metrics={"leads": "from brand channels", "conversion_rate": "leads→clients"}),
    }

    codex = FounderBrandCodex(
        positioning_core=positioning_core,
        narrative_buckets=narrative_buckets,
        audience_resonance_map=audience_resonance_map,
        voice=voice,
        content_mapping=content_mapping,
        asymmetric_moves=asymmetric_moves,
        measurement=measurement,
    )
    return FounderBrandResponse(codex=codex)

