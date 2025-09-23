from __future__ import annotations

"""
Agent Tools Toolkit

Declarative tool registry and helpers to bind a shared set of utility tools
to any LLM used by agents. Tools wrap the shared services from services.registry.

Usage:
    from agents.utils.toolkit import get_toolkit, bind_llm_with_tools
    llm = bind_llm_with_tools(get_services().llm_reasoning, ["web_search","scrape_text"]).with_structured_output(Model)
"""

from typing import List, Optional, Dict, Callable
from pydantic import BaseModel, Field, HttpUrl
from langchain_core.tools import tool, BaseTool

from services.registry import get_services


_TOOL_REGISTRY: Dict[str, BaseTool] = {}


def _register(t: BaseTool) -> None:
    _TOOL_REGISTRY[t.name] = t


# --- Schemas ---
class SearchArgs(BaseModel):
    query: str
    max_results: int = Field(5, ge=1, le=25)


class ScrapeArgs(BaseModel):
    url: HttpUrl
    max_chars: int = Field(4000, ge=200, le=20000)


class PreviewArgs(BaseModel):
    url: HttpUrl


class SummarizeArgs(BaseModel):
    text: str
    mode: str = Field("concise")


class KeywordsArgs(BaseModel):
    text: str
    top_k: int = Field(10, ge=3, le=50)


class TranslateArgs(BaseModel):
    text: str
    language: str = Field("en")


class NearbyArgs(BaseModel):
    latitude: float
    longitude: float
    radius: int = Field(1500, ge=100, le=50000)
    poi_type: Optional[str] = None
    keyword: Optional[str] = None


class ReverseGeocodeArgs(BaseModel):
    latitude: float
    longitude: float


# --- Core Tools ---
@tool("web_search", args_schema=SearchArgs)
def web_search(query: str, max_results: int = 5) -> str:
    """Search the web and return a JSON list of {title, url, snippet}."""
    svc = get_services().search
    items = []
    try:
        for it in svc.search_sync(query, max_results=max_results):  # type: ignore[attr-defined]
            items.append({
                "title": getattr(it, "title", ""),
                "url": getattr(it, "url", ""),
                "snippet": getattr(it, "snippet", getattr(it, "text", "")),
            })
    except Exception:
        # Async-only service fallback
        pass
    import json
    return json.dumps(items[:max_results])


@tool("scrape_text", args_schema=ScrapeArgs)
def scrape_text(url: str, max_chars: int = 4000) -> str:
    """Fetch and return cleaned text content from a URL (truncated)."""
    svc = get_services().scraper
    try:
        text = svc.scrape_text_sync(url)  # type: ignore[attr-defined]
    except Exception:
        text = ""
    return (text or "")[:max_chars]


@tool("link_preview", args_schema=PreviewArgs)
def link_preview(url: str) -> str:
    """Return a small JSON with title and description for a URL."""
    svc = get_services().link_preview
    p = svc.fetch_sync(url) if hasattr(svc, "fetch_sync") else None  # type: ignore
    import json
    return json.dumps({
        "title": getattr(p, "title", ""),
        "description": getattr(p, "description", ""),
    })


@tool("summarize_text", args_schema=SummarizeArgs)
def summarize_text(text: str, mode: str = "concise") -> str:
    """Summarize text (concise|detailed)."""
    return get_services().summarizer.summarize_sync(text, mode=mode) if hasattr(get_services().summarizer, "summarize_sync") else text[:1500]  # type: ignore


@tool("extract_keywords", args_schema=KeywordsArgs)
def extract_keywords(text: str, top_k: int = 10) -> str:
    """Extract top keywords from text and return a CSV line."""
    kws = get_services().keywords.extract_sync(text, top_k=top_k) if hasattr(get_services().keywords, "extract_sync") else []  # type: ignore
    return ",".join(kws or [])


@tool("translate_text", args_schema=TranslateArgs)
def translate_text(text: str, language: str = "en") -> str:
    """Translate text to a target language code (e.g., en, hi)."""
    svc = get_services().translate
    try:
        return svc.translate_sync(text, language)  # type: ignore[attr-defined]
    except Exception:
        return text


@tool("maps_nearby", args_schema=NearbyArgs)
def maps_nearby(latitude: float, longitude: float, radius: int = 1500, poi_type: Optional[str] = None, keyword: Optional[str] = None) -> str:
    """Find nearby POIs using Google Maps. Returns JSON list of {name, lat, lng, types, ratings_total}."""
    m = get_services().maps
    import json
    try:
        pois = m.nearby_search_sync((latitude, longitude), radius=radius, poi_type=poi_type, keyword=keyword)  # type: ignore[attr-defined]
    except Exception:
        pois = []
    out = []
    for p in pois or []:
        lat, lng = p.location if hasattr(p, "location") else (latitude, longitude)
        out.append({"name": getattr(p, "name", ""), "lat": lat, "lng": lng, "types": getattr(p, "types", []), "ratings_total": getattr(p, "user_ratings_total", 0)})
    return json.dumps(out)


@tool("maps_reverse_geocode", args_schema=ReverseGeocodeArgs)
def maps_reverse_geocode(latitude: float, longitude: float) -> str:
    """Reverse geocode lat/lng to a human-friendly address."""
    try:
        geo = get_services().maps.geocode_sync(latitude, longitude)  # type: ignore[attr-defined]
        import json
        return json.dumps({"formatted_address": geo.get("formatted_address", "") if geo else ""})
    except Exception:
        return "{}"


def get_toolkit(names: Optional[List[str]] = None) -> List[BaseTool]:
    """Return a list of tools by name or all tools if names is None."""
    # Ensure tools are registered exactly once
    if not _TOOL_REGISTRY:
        # Trigger decorator registration by referencing functions
        for t in [web_search, scrape_text, link_preview, summarize_text, extract_keywords, translate_text, maps_nearby, maps_reverse_geocode]:
            _register(t)
    if names:
        return [t for n, t in _TOOL_REGISTRY.items() if n in names]
    return list(_TOOL_REGISTRY.values())


def bind_llm_with_tools(llm, names: Optional[List[str]] = None):
    """Bind a chat model with the given tools (or all)."""
    tools = get_toolkit(names)
    try:
        return llm.bind_tools(tools)
    except Exception:
        # If binding unsupported, return llm unchanged
        return llm

