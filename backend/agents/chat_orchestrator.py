import base64
import logging
from typing import List, Dict

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from agents.utils.toolkit import bind_llm_with_tools, get_toolkit

from services.registry import get_services
from services.calendar_service import build_ics_event
from services.pdf_writer_service import make_simple_pdf_base64

from schemas.chat_schemas import ChatTurnRequest, ChatTurnResponse, Attachment, ActionLog
from agents.deep_research_agent import run_deep_research
from agents.social_calendar_agent import run_social_calendar
from agents.ad_copy_agent import run_ad_copy
from agents.image_prompt_agent import run_image_prompt
from agents.thread_agent import run_thread
from agents.evidence_linker_agent import run_copy_evidence_audit


logger = logging.getLogger(__name__)


class RouterTool(BaseModel):
    ask_clarify: bool = False
    questions: List[str] = Field(default_factory=list)
    tasks: List[Dict] = Field(default_factory=list, description="List of actions with type and params")


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


async def run_chat_orchestrator(req: ChatTurnRequest) -> ChatTurnResponse:
    # 1) Route intent (graceful fallback if LLM offline)
    forced_mentions = []
    try:
        import re
        forced_mentions = re.findall(r"@([a-zA-Z_]+)", req.user_message)
    except Exception:
        pass

    router = bind_llm_with_tools(_reason(), ["web_search", "extract_keywords"]).with_structured_output(RouterTool)
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a strategic marketing orchestrator. Decide if you must ask clarifying questions or perform tasks."
            " Allowed tasks: research, social_calendar, offer_assets, evidence_audit, schedule, email_draft, pdf_brief, map_lookup, canva_design, oauth_connect."
            " Return a JSON with ask_clarify(bool), questions(list), and tasks(list of {type, params}). Keep tasks minimal and specific.",
        ),
        ("human", "User: {msg}\nHints: location={loc}, start={start}, end={end}, email_to={email}"),
    ])
    try:
        plan = await (prompt | router).ainvoke(
            {
                "msg": req.user_message,
                "loc": req.location_query or "",
                "start": req.start_datetime_iso or "",
                "end": req.end_datetime_iso or "",
                "email": req.email_to or "",
            }
        )
    except Exception:
        # LLM not reachable; degrade gracefully
        safe_msg = (
            "The AI planner is temporarily unavailable. You can still use fallback tools: "
            "@schedule, @email_draft, @pdf_brief."
        )
        # If user forced any safe tools, run them directly
        safe = {"schedule", "email_draft", "pdf_brief"}
        forced = set((req.forced_tools or []) + forced_mentions)
        run_now = [t for t in forced if t in safe]
        if not run_now:
            return ChatTurnResponse(assistant_message=safe_msg, clarifying_questions=[], actions=[], attachments=[])
        # Build a pseudo-plan with safe tasks only
        plan = RouterTool(ask_clarify=False, questions=[], tasks=[{"type": t, "params": {}} for t in run_now])

    # Parse @tool mentions to force-run tasks
    forced = set((req.forced_tools or []) + forced_mentions)
    if plan.ask_clarify and not forced:
        return ChatTurnResponse(
            assistant_message="I need a couple of details to proceed.",
            clarifying_questions=plan.questions,
        )

    actions: List[ActionLog] = []
    attachments: List[Attachment] = []
    assistant_lines: List[str] = []

    # 2) Execute tasks
    tasks = list(plan.tasks)
    for f in forced:
        tasks.append({"type": f, "params": {}})
    for t in tasks:
        ttype = (t.get("type") or "").lower()
        params = t.get("params") or {}
        try:
            import json

            if ttype == "research":
                q = params.get("query") or req.user_message
                res = await run_deep_research({"query": q, "max_results": 8, "max_pages": 6})
                attachments.append(
                    Attachment(
                        name="research.json",
                        mime="application/json",
                        base64=base64.b64encode(json.dumps(res).encode()).decode(),
                    )
                )
                assistant_lines.append("Attached research findings.")
            elif ttype == "social_calendar":
                topic = params.get("topic") or req.user_message
                cal = await run_social_calendar({"topic": topic, "weeks": 2, "posts_per_week": 7})
                attachments.append(
                    Attachment(
                        name="social_calendar.json",
                        mime="application/json",
                        base64=base64.b64encode(json.dumps(cal).encode()).decode(),
                    )
                )
                assistant_lines.append("Queued social calendar draft.")
            elif ttype == "offer_assets":
                topic = params.get("topic") or req.user_message
                ad = await run_ad_copy(
                    {"product_summary": topic, "platforms": ["facebook", "instagram"], "call_to_action": "Learn more"}
                )
                img = await run_image_prompt({"concept": topic, "style": "studio photography"})
                th = await run_thread({"topic": topic, "platform": "twitter", "posts": 8})
                attachments.append(
                    Attachment(
                        name="ad_copy.json",
                        mime="application/json",
                        base64=base64.b64encode(json.dumps(ad).encode()).decode(),
                    )
                )
                attachments.append(
                    Attachment(
                        name="image_prompt.json",
                        mime="application/json",
                        base64=base64.b64encode(json.dumps(img).encode()).decode(),
                    )
                )
                attachments.append(
                    Attachment(
                        name="thread.json",
                        mime="application/json",
                        base64=base64.b64encode(json.dumps(th).encode()).decode(),
                    )
                )
                assistant_lines.append("Drafted ad copy, image prompts, and a thread.")
            elif ttype == "evidence_audit":
                copy = params.get("copy") or req.user_message
                audit = await run_copy_evidence_audit({"copy_text": copy})
                attachments.append(
                    Attachment(
                        name="evidence_audit.json",
                        mime="application/json",
                        base64=base64.b64encode(json.dumps(audit).encode()).decode(),
                    )
                )
                assistant_lines.append("Evidence audit attached with rewrite suggestions.")
            elif ttype == "schedule":
                title = params.get("title") or "Marketing Event"
                desc = params.get("description") or req.user_message
                start = params.get("start") or req.start_datetime_iso or "2025-01-01T10:00:00Z"
                end = params.get("end") or req.end_datetime_iso or "2025-01-01T11:00:00Z"
                loc = params.get("location") or req.location_query or ""
                ics = build_ics_event(title, desc, start, end, loc)
                attachments.append(
                    Attachment(
                        name="event.ics",
                        mime="text/calendar",
                        base64=base64.b64encode(ics.encode()).decode(),
                    )
                )
                assistant_lines.append("Added calendar event.")
            elif ttype == "email_draft":
                to = params.get("to") or req.email_to or "ops@example.com"
                subject = params.get("subject") or "Plan for offer launch"
                body = params.get("body") or (
                    f"Hi,\n\nHere is the plan based on your request: {req.user_message}\n\n— Assistant"
                )
                eml = f"To: {to}\nSubject: {subject}\n\n{body}"
                attachments.append(
                    Attachment(
                        name="email.txt",
                        mime="text/plain",
                        base64=base64.b64encode(eml.encode()).decode(),
                    )
                )
                assistant_lines.append("Drafted an email.")
            elif ttype == "pdf_brief":
                title = params.get("title") or "Execution Brief"
                body = params.get("body") or f"Summary based on: {req.user_message}"
                pdf_b64 = make_simple_pdf_base64(title, body)
                attachments.append(Attachment(name="brief.pdf", mime="application/pdf", base64=pdf_b64))
                assistant_lines.append("Attached a PDF brief.")
            elif ttype in ("map_lookup",):
                assistant_lines.append("Maps lookup is a placeholder in this build.")
                actions.append(ActionLog(type=ttype, status="skipped", details="placeholder"))
            else:
                actions.append(ActionLog(type=ttype, status="skipped", details="unknown task"))
                continue

            actions.append(ActionLog(type=ttype, status="ok", details=""))
        except Exception as e:
            logger.error(f"Chat task '{ttype}' failed: {e}", exc_info=True)
            actions.append(ActionLog(type=ttype, status="error", details=str(e)))

    message = "\n".join(assistant_lines) or "Done. What next?"
    return ChatTurnResponse(
        assistant_message=message, clarifying_questions=[], actions=actions, attachments=attachments
    )


async def stream_chat_events(req: ChatTurnRequest):
    # SSE generator: yields events as tasks progress
    try:
        # Try to plan with LLM; if offline, fall back to safe tools if forced
        router = _reason().with_structured_output(RouterTool)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a strategic marketing orchestrator. Decide tasks. Allowed tasks: research, social_calendar,"
                    " offer_assets, evidence_audit, schedule, email_draft, pdf_brief, map_lookup, canva_design, oauth_connect.",
                ),
                ("human", "User: {msg}"),
            ]
        )
        try:
            plan = await (prompt | router).ainvoke({"msg": req.user_message})
        except Exception:
            import re
            mentions = re.findall(r"@([a-zA-Z_]+)", req.user_message)
            forced = set((req.forced_tools or []) + mentions)
            safe = {"schedule", "email_draft", "pdf_brief"}
            run_now = [t for t in forced if t in safe]
            plan = RouterTool(ask_clarify=not bool(run_now), questions=["Which fallback tool should I run? e.g., @schedule"], tasks=[{"type": t, "params": {}} for t in run_now])

        # Parse @ mentions and forced_tools
        import re

        mentions = re.findall(r"@([a-zA-Z_]+)", req.user_message)
        forced = set((req.forced_tools or []) + mentions)
        tasks = list(plan.tasks)
        for f in forced:
            tasks.append({"type": f, "params": {}})

        # Yield clarifications if needed and no forced
        if plan.ask_clarify and not forced:
            payload = {"type": "clarify", "questions": plan.questions}
            yield f"event: message\ndata: {payload}\n\n"
            return

        # Execute tasks sequentially, streaming progress
        async def emit(obj):
            import json

            yield f"event: message\ndata: {json.dumps(obj)}\n\n"

        # Start
        async for chunk in emit({"type": "start", "message": "Processing tasks"}):
            yield chunk

        for t in tasks:
            ttype = (t.get("type") or "").lower()
            params = t.get("params") or {}
            async for chunk in emit({"type": "task_start", "task": ttype}):
                yield chunk
            try:
                if ttype == "research":
                    q = params.get("query") or req.user_message
                    res = await run_deep_research({"query": q, "max_results": 8, "max_pages": 6})
                    async for chunk in emit(
                        {"type": "attachment", "name": "research.json", "mime": "application/json", "content": res}
                    ):
                        yield chunk
                elif ttype == "social_calendar":
                    topic = params.get("topic") or req.user_message
                    cal = await run_social_calendar({"topic": topic, "weeks": 2, "posts_per_week": 7})
                    async for chunk in emit(
                        {
                            "type": "attachment",
                            "name": "social_calendar.json",
                            "mime": "application/json",
                            "content": cal,
                        }
                    ):
                        yield chunk
                elif ttype == "offer_assets":
                    topic = params.get("topic") or req.user_message
                    ad = await run_ad_copy(
                        {"product_summary": topic, "platforms": ["facebook", "instagram"], "call_to_action": "Learn more"}
                    )
                    img = await run_image_prompt({"concept": topic, "style": "studio photography"})
                    th = await run_thread({"topic": topic, "platform": "twitter", "posts": 8})
                    async for chunk in emit(
                        {"type": "attachment", "name": "ad_copy.json", "mime": "application/json", "content": ad}
                    ):
                        yield chunk
                    async for chunk in emit(
                        {"type": "attachment", "name": "image_prompt.json", "mime": "application/json", "content": img}
                    ):
                        yield chunk
                    async for chunk in emit(
                        {"type": "attachment", "name": "thread.json", "mime": "application/json", "content": th}
                    ):
                        yield chunk
                elif ttype == "evidence_audit":
                    copy = params.get("copy") or req.user_message
                    audit = await run_copy_evidence_audit({"copy_text": copy})
                    async for chunk in emit(
                        {
                            "type": "attachment",
                            "name": "evidence_audit.json",
                            "mime": "application/json",
                            "content": audit,
                        }
                    ):
                        yield chunk
                elif ttype == "schedule":
                    title = params.get("title") or "Marketing Event"
                    desc = params.get("description") or req.user_message
                    start = params.get("start") or req.start_datetime_iso or "2025-01-01T10:00:00Z"
                    end = params.get("end") or req.end_datetime_iso or "2025-01-01T11:00:00Z"
                    loc = params.get("location") or req.location_query or ""
                    ics = build_ics_event(title, desc, start, end, loc)
                    async for chunk in emit(
                        {
                            "type": "attachment_base64",
                            "name": "event.ics",
                            "mime": "text/calendar",
                            "base64": base64.b64encode(ics.encode()).decode(),
                        }
                    ):
                        yield chunk
                elif ttype == "email_draft":
                    to = params.get("to") or req.email_to or "ops@example.com"
                    subject = params.get("subject") or "Plan for offer launch"
                    body = params.get("body") or (
                        f"Hi,\n\nHere is the plan based on your request: {req.user_message}\n\n— Assistant"
                    )
                    eml = f"To: {to}\nSubject: {subject}\n\n{body}"
                    async for chunk in emit(
                        {
                            "type": "attachment_base64",
                            "name": "email.txt",
                            "mime": "text/plain",
                            "base64": base64.b64encode(eml.encode()).decode(),
                        }
                    ):
                        yield chunk
                elif ttype == "pdf_brief":
                    title = params.get("title") or "Execution Brief"
                    body = params.get("body") or f"Summary based on: {req.user_message}"
                    pdf_b64 = make_simple_pdf_base64(title, body)
                    async for chunk in emit(
                        {
                            "type": "attachment_base64",
                            "name": "brief.pdf",
                            "mime": "application/pdf",
                            "base64": pdf_b64,
                        }
                    ):
                        yield chunk
                elif ttype in ("oauth_connect", "connect"):
                    provider = (params.get("provider") or "canva").lower()
                    try:
                        url = get_services().oauth.build_authorize_url(provider, uid="default")
                        async for chunk in emit({"type": "message", "message": f"Connect {provider}: {url}"}):
                            yield chunk
                    except Exception as e:
                        async for chunk in emit(
                            {"type": "message", "message": f"Unable to build connect link for {provider}: {e}"}
                        ):
                            yield chunk
                else:
                    async for chunk in emit({"type": "task_skipped", "task": ttype, "reason": "unknown"}):
                        yield chunk
                    continue
                async for chunk in emit({"type": "task_done", "task": ttype}):
                    yield chunk
            except Exception as e:
                async for chunk in emit({"type": "task_error", "task": ttype, "error": str(e)}):
                    yield chunk
        async for chunk in emit({"type": "done", "message": "All tasks complete"}):
            yield chunk
    except Exception as e:
        import json

        yield f"event: message\ndata: {json.dumps({'type':'error','error':str(e)})}\n\n"
