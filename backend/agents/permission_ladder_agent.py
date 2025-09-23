from __future__ import annotations

from schemas.permission_ladder_schemas import (
    PermissionLadderRequest,
    PermissionLadderResponse,
    PermissionLadderBlueprint,
    ReciprocityOffer,
    MicroAsk,
    PromptSpec,
    OptInStep,
    CommunityEntry,
    GrowthLoop,
)


def build_permission_ladder(req: PermissionLadderRequest) -> PermissionLadderResponse:
    audience_identity = [
        {"who_we_are": "Builders who ship before they brag"},
        {"what_we_value": "useful outputs, not theater"},
    ]

    offers = [
        ReciprocityOffer(title="1‑page playbook", asset_url="https://example.com/onepager.pdf"),
    ]

    micro_asks = [
        MicroAsk(label="Pick topic A/B", time_to_do="10s", success_criteria="preference saved"),
    ]

    prompts = [
        PromptSpec(rung="R1", type="Facilitator", copy="Send me the 1‑pager", trigger_timing="D0+0m"),
        PromptSpec(rung="R2", type="Signal", copy="Confirm topic pref", trigger_timing="D0+5m"),
    ]

    sequence = [
        OptInStep(
            send_at="D0+0m",
            subject="Can I borrow 17 seconds to unlock the playbook?",
            body_outline="One line value, one button, transparent consent",
            legal_block="Freely given, specific, informed, unambiguous; one‑click opt‑out",
        ),
        OptInStep(
            send_at="D0+5m",
            subject="Pick your lane. I will tune what you get.",
            body_outline="Two toggles and a 60s how‑to video",
            legal_block="GDPR consent copy with link to prefs",
        ),
    ]

    entries = [
        CommunityEntry(channel="Discord", purpose="Orientation + artifacts", capacity_cap=150),
        CommunityEntry(channel="WhatsApp", purpose="Narrow cohort alerts", capacity_cap=150),
    ]

    cadence = {
        "weekly_heartbeat": True,
        "caps": {"emails_per_week_max": 2, "dm_prompts_per_week_max": 1},
        "signals_first": True,
    }

    loops = [
        GrowthLoop(
            name="content_loop",
            input="member win",
            process="curate → newsletter highlight → social post",
            output="new subscribers",
            reinvestment="proof visible on arrival",
        ),
        GrowthLoop(
            name="invite_loop",
            input="AMA slot",
            process="bring 1 qualified peer",
            output="warm referral",
            reinvestment="peer enters at R1",
        ),
    ]

    kpis = {
        "micro_consent_rate": "",
        "R3_join_rate": "",
        "contribution_rate_R4": "",
        "loop_yield": "",
    }

    compliance = {
        "consent_text": "Freely given, specific, informed, unambiguous; clear affirmative action.",
        "data_map_link": "https://example.com/data-map",
        "unsubscribe_link": "https://example.com/unsubscribe",
    }

    bp = PermissionLadderBlueprint(
        audience_identity=audience_identity,
        reciprocity_offers=offers,
        micro_asks=micro_asks,
        prompts=prompts,
        opt_in_sequence=sequence,
        community_entry_points=entries,
        cadence_rules=cadence,
        growth_loops=loops,
        kpis=kpis,
        compliance=compliance,
    )
    return PermissionLadderResponse(blueprint=bp)

