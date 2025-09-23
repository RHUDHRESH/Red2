import logging
from typing import TypedDict

from agents.synthetic_behavior_agent import run_synthetic_generation
from agents.icp_builder_agent import run_icp_builder_agent
from agents.cohort_agent import run_cohort_strategist_agent
from schemas.synthetic_schemas import SyntheticGenRequest
from schemas.geo_schemas import MarketNeedReport, GeoSignal


logger = logging.getLogger(__name__)


class PipelineState(TypedDict):
    synthetic: dict
    icp_report: dict | None
    cohort_strategy_report: dict | None
    error: str | None


def _to_market_report(synth: dict) -> MarketNeedReport:
    # Construct a coarse MarketNeedReport from synthetic datasets
    datasets = synth.get("cohorts", [])
    demand_hotspots: list[GeoSignal] = []
    pain_topics: dict[str, float] = {}
    total = 0
    for ds in datasets:
        cohort = ds.get("cohort", "cohort")
        people = ds.get("people", [])
        n = len(people)
        total += n
        # build a hotspot summary; lat/lng are unknown (0.0)
        demand_hotspots.append(
            GeoSignal(
                poi_name=cohort,
                poi_type="office",
                headcount=max(10, n),
                distance_m=1000,
                travel_time_min=10,
                reach_score=float(max(10, n) / 10.0),
                latitude=0.0,
                longitude=0.0,
            )
        )
        # Aggregate pain points
        for p in people[:200]:
            if isinstance(p, dict):
                pps = p.get("pain_points", [])
            else:
                try:
                    pps = p.pain_points
                except Exception:
                    pps = []
            for pp in pps:
                pain_topics[pp] = pain_topics.get(pp, 0.0) + 1.0
    # Normalize pain topics to frequencies
    total_pp = sum(pain_topics.values()) or 1.0
    for k in list(pain_topics.keys()):
        pain_topics[k] = round(pain_topics[k] / total_pp, 3)
    final_score = float(len(demand_hotspots)) * 10.0
    verdict = "PASS" if final_score >= 10.0 else "FAIL"
    return MarketNeedReport(
        demand_hotspots=demand_hotspots,
        competitor_count=10,
        median_price=250,
        price_gap_pct=15.0,
        pain_topics=pain_topics,
        final_score=final_score,
        verdict=verdict,
    )


async def run_synthetic_icp_pipeline(req_dict: dict) -> dict:
    logger.info("--- Running Synthetic → ICP Pipeline ---")
    try:
        synthetic = await run_synthetic_generation(req_dict)
        if "error" in synthetic:
            return {"error": synthetic["error"]}
        market = _to_market_report(synthetic)
        icp = await run_icp_builder_agent(market.model_dump())
        if "error" in icp:
            return {"error": icp["error"]}
        cohort = await run_cohort_strategist_agent(icp)
        return {
            "synthetic": synthetic,
            "icp_report": icp,
            "cohort_strategy_report": cohort,
        }
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        return {"error": "A critical error occurred in the synthetic→ICP pipeline."}
