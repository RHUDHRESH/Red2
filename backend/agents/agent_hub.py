import asyncio
import logging
from typing import Any, Dict, List

from schemas.a2a_schemas import WorkflowRequest, WorkflowResult, TaskEvent

from agents.deep_research_agent import run_deep_research
from agents.competitor_intel_agent import run_competitor_scan
from agents.market_analysis_agent import run_market_analysis_agent
from agents.icp_builder_agent import run_icp_builder_agent
from agents.positioning_agent import run_positioning_agent
from agents.social_calendar_agent import run_social_calendar
from agents.ad_copy_agent import run_ad_copy
from agents.image_prompt_agent import run_image_prompt
from agents.thread_agent import run_thread
from agents.evidence_linker_agent import run_copy_evidence_audit
from agents.seo_brief_agent import run_seo_brief
from agents.partner_outreach_agent import run_partner_outreach
from agents.synthetic_behavior_agent import run_synthetic_generation
from agents.synthetic_pipeline_agent import run_synthetic_icp_pipeline
from agents.strategy_engine import (
    run_segment, run_wound, run_reframe, run_offer, run_action, run_cash,
    run_cashguard, run_permission, run_lateral_vertical, run_aisas,
)
from agents.objective_router_agent import run_objective_router
from schemas.strategy_schemas import (
    SegmentRequest, WoundRequest, ReframeRequest, OfferRequest, ActionRequest,
    CashRequest, CashGuardRequest, PermissionRequest, LateralVerticalRequest, AISASRequest,
)
from schemas.competitor_schemas import CompetitorScanRequest
from schemas.geo_schemas import LocationRequest, MarketNeedReport
from schemas.positioning_schemas import PositioningGenerationRequest


logger = logging.getLogger(__name__)


AGENT_REGISTRY = {
    "research": run_deep_research,
    "competitors_scan": run_competitor_scan,
    "market_analysis": run_market_analysis_agent,
    "icp_builder": run_icp_builder_agent,
    "positioning": run_positioning_agent,
    "social_calendar": run_social_calendar,
    "ad_copy": run_ad_copy,
    "image_prompt": run_image_prompt,
    "thread": run_thread,
    "evidence_audit": run_copy_evidence_audit,
    "seo_brief": run_seo_brief,
    "partner_outreach": run_partner_outreach,
    "synthetic_generate": run_synthetic_generation,
    "synthetic_icp_pipeline": run_synthetic_icp_pipeline,
    # strategy micro agents
    "strategy_segment": run_segment,
    "strategy_wound": run_wound,
    "strategy_reframe": run_reframe,
    "strategy_offer": run_offer,
    "strategy_action": run_action,
    "strategy_cash": run_cash,
    "strategy_cashguard": run_cashguard,
    "strategy_permission": run_permission,
    "strategy_lateral_vertical": run_lateral_vertical,
    "strategy_aisas": run_aisas,
    "objective_router": run_objective_router,
}

AGENT_INPUT_MODELS = {
    "strategy_segment": SegmentRequest,
    "strategy_wound": WoundRequest,
    "strategy_reframe": ReframeRequest,
    "strategy_offer": OfferRequest,
    "strategy_action": ActionRequest,
    "strategy_cash": CashRequest,
    "strategy_cashguard": CashGuardRequest,
    "strategy_permission": PermissionRequest,
    "strategy_lateral_vertical": LateralVerticalRequest,
    "strategy_aisas": AISASRequest,
    # objective router
    "objective_router": None,  # accepts dict
    # new entries
    "competitors_scan": CompetitorScanRequest,
    "market_analysis": LocationRequest,
    "icp_builder": MarketNeedReport,
    "positioning": PositioningGenerationRequest,
}


def _get_from_context(ctx: Dict[str, Any], path: str) -> Any:
    # path like tasks.task_id.key → ctx[task_id][key]
    parts = path.split(".")
    if parts and parts[0] == "tasks":
        parts = parts[1:]
    cur: Any = ctx
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return None
    return cur


def _resolve_templates(obj: Any, ctx: Dict[str, Any]) -> Any:
    if isinstance(obj, str):
        # replace {{...}} with context value string form
        import re
        def repl(m):
            key = m.group(1).strip()
            val = _get_from_context(ctx, key)
            return str(val) if val is not None else ""
        return re.sub(r"\{\{([^}]+)\}\}", repl, obj)
    if isinstance(obj, list):
        return [_resolve_templates(x, ctx) for x in obj]
    if isinstance(obj, dict):
        return {k: _resolve_templates(v, ctx) for k, v in obj.items()}
    return obj


async def run_workflow(req: WorkflowRequest) -> WorkflowResult:
    context: Dict[str, Any] = {}
    events: List[TaskEvent] = []
    remaining = {t.id: t for t in req.tasks}
    completed: set[str] = set()
    while remaining:
        progressed = False
        for tid, task in list(remaining.items()):
            if any(dep not in completed for dep in task.depends_on):
                continue
            events.append(TaskEvent(task_id=tid, type="TASK_STARTED", message=task.agent))
            func = AGENT_REGISTRY.get(task.agent)
            if not func:
                err = f"Unknown agent: {task.agent}"
                events.append(TaskEvent(task_id=tid, type="TASK_FAILED", message=err))
                if task.on_error == "stop":
                    return WorkflowResult(run_id=req.run_id, status="failed", context=context, events=events, error=err)
                completed.add(tid)
                remaining.pop(tid, None)
                progressed = True
                continue
            try:
                inp = _resolve_templates(task.input, context)
                # Convert to Pydantic model if required
                model_cls = AGENT_INPUT_MODELS.get(task.agent)
                call_arg = inp
                if model_cls is not None:
                    try:
                        call_arg = model_cls(**inp)
                    except Exception:
                        # If conversion fails, keep dict and let agent handle
                        call_arg = inp
                result = await func(call_arg) if asyncio.iscoroutinefunction(func) else func(call_arg)
                # Normalize result into plain dict for downstream templating
                if hasattr(result, "model_dump"):
                    context[tid] = result.model_dump()  # type: ignore
                else:
                    context[tid] = result
                events.append(TaskEvent(task_id=tid, type="TASK_COMPLETED", message="ok"))
                completed.add(tid)
                remaining.pop(tid, None)
                progressed = True
            except Exception as e:
                err = f"{e}"
                logger.error(f"Agent task failed: {tid}/{task.agent}: {e}", exc_info=True)
                events.append(TaskEvent(task_id=tid, type="TASK_FAILED", message=err))
                if task.on_error == "stop":
                    return WorkflowResult(run_id=req.run_id, status="failed", context=context, events=events, error=err)
                completed.add(tid)
                remaining.pop(tid, None)
                progressed = True
        if not progressed:
            # cyclic or waiting; bail out
            return WorkflowResult(run_id=req.run_id, status="failed", context=context, events=events, error="Unresolved dependencies or no progress")
    return WorkflowResult(run_id=req.run_id, status="completed", context=context, events=events)
