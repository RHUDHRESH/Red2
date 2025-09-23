from __future__ import annotations

import logging
from typing import Optional, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.deep_research_agent import run_deep_research
from agents.competitor_intel_agent import run_competitor_scan
from agents.market_analysis_agent import run_market_analysis_agent
from agents.icp_builder_agent import run_icp_builder_agent
from agents.positioning_agent import run_positioning_agent

from schemas.research_schemas import ResearchResponse
from schemas.competitor_schemas import CompetitorScanResponse
from schemas.geo_schemas import MarketNeedReport
from schemas.icp_schemas import ICPReport
from schemas.positioning_schemas import PositioningResponse


logger = logging.getLogger(__name__)


class IntakeOrchestrateRequest(BaseModel):
    captured: Dict[str, str] = Field(default_factory=dict)
    summary: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    include_positioning: bool = True


class IntakeOrchestrateResponse(BaseModel):
    research: Optional[ResearchResponse] = None
    competitors: Optional[CompetitorScanResponse] = None
    market_report: Optional[MarketNeedReport] = None
    icp: Optional[ICPReport] = None
    positioning: Optional[PositioningResponse] = None


router = APIRouter()


@router.post("/orchestrate", response_model=IntakeOrchestrateResponse)
async def orchestrate_from_intake(req: IntakeOrchestrateRequest):
    """Convenience endpoint that chains research → competitor scan → (optional) maps+ICP → (optional) positioning.

    This endpoint is intentionally resilient: missing steps are skipped rather than failing the whole flow.
    """
    captured = req.captured or {}
    result: Dict[str, object] = {}

    # 1) Research
    query = captured.get("one_line_offer") or captured.get("story_trigger") or (req.summary or "market research")
    try:
        research = await run_deep_research({"query": query, "max_results": 8, "max_pages": 6, "include_domains": [], "exclude_domains": [], "language": "en"})
        if isinstance(research, dict) and research.get("error"):
            logger.warning(f"[orchestrate] research error: {research['error']}")
            research = None
        result["research"] = research
    except Exception as e:
        logger.warning(f"[orchestrate] research failed: {e}")
        result["research"] = None

    # 2) Competitors
    try:
        competitors = await run_competitor_scan({"query": query, "max_candidates": 12, "per_source": 6})
        if isinstance(competitors, dict) and competitors.get("error"):
            logger.warning(f"[orchestrate] competitors error: {competitors['error']}")
            competitors = None
        result["competitors"] = competitors
    except Exception as e:
        logger.warning(f"[orchestrate] competitors failed: {e}")
        result["competitors"] = None

    # 3) Market analysis via Maps (optional)
    icp = None
    market = None
    if req.latitude is not None and req.longitude is not None:
        try:
            market = await run_market_analysis_agent({
                "address": req.address or (captured.get("location") or ""),
                "latitude": float(req.latitude),
                "longitude": float(req.longitude),
            })
            if isinstance(market, dict) and market.get("error"):
                logger.warning(f"[orchestrate] market analysis error: {market['error']}")
                market = None
            else:
                try:
                    icp = await run_icp_builder_agent(market)
                    if isinstance(icp, dict) and icp.get("error"):
                        logger.warning(f"[orchestrate] icp error: {icp['error']}")
                        icp = None
                except Exception as e:
                    logger.warning(f"[orchestrate] icp failed: {e}")
                    icp = None
        except Exception as e:
            logger.warning(f"[orchestrate] market analysis failed: {e}")
            market, icp = None, None
    result["market_report"] = market
    result["icp"] = icp

    # 4) Positioning (optional)
    if req.include_positioning:
        try:
            facts = []
            if captured.get("one_line_offer"): facts.append(f"Offer: {captured['one_line_offer']}")
            if captured.get("price_band"): facts.append(f"Price band: {captured['price_band']}")
            if captured.get("capacity_limit"): facts.append(f"Capacity: {captured['capacity_limit']}")
            if captured.get("budget_cap_kill"): facts.append(f"Budget/Kill-line: {captured['budget_cap_kill']}")
            if captured.get("location"): facts.append(f"Location: {captured['location']}")
            if captured.get("proof_link"): facts.append(f"Proof: {captured['proof_link']}")
            claims = []
            if captured.get("story_trigger"): claims.append(captured["story_trigger"])  # treat as origin claim
            positioning = await run_positioning_agent({"facts": facts, "claims": claims, "taboos": []})
            if isinstance(positioning, dict) and positioning.get("error"):
                logger.warning(f"[orchestrate] positioning error: {positioning['error']}")
                positioning = None
            result["positioning"] = positioning
        except Exception as e:
            logger.warning(f"[orchestrate] positioning failed: {e}")
            result["positioning"] = None

    return result

