from __future__ import annotations

from typing import List

from services.registry import get_services
from schemas.ops_schemas import VibeCheckRequest, VibeCheckResponse, ChecklistItem, SourceRef


LINKEDIN = "LinkedIn"
SMT = "Social Media Today"
INSIDER = "Business Insider"
YTPOLARIS = "yt.polarismedia.de"
YOUTUBE_BLOG = "YouTube Blog"


async def _refs() -> List[SourceRef]:
    rss = get_services().rss
    out: List[SourceRef] = []
    feeds = [
        (SMT, "https://www.socialmediatoday.com/rss"),
        (INSIDER, "https://www.businessinsider.com/rss"),
        (YOUTUBE_BLOG, "https://blog.youtube/inside-youtube/feeds/atom/"),
    ]
    for name, url in feeds:
        try:
            items = await rss.parse(url)
            if items:
                out.append(SourceRef(title=items[0].title, url=items[0].url, source=name))
        except Exception:
            continue
    # Static refs for LinkedIn and yt.polarismedia.de explainer
    out.append(SourceRef(title="LinkedIn Transparency & Ranking", url="https://www.linkedin.com/help/linkedin/answer/a507663", source=LINKEDIN))
    out.append(SourceRef(title="YouTube recommendations & satisfaction signals", url="https://yt.polarismedia.de/", source=YTPOLARIS))
    return out


async def run_platform_vibe_check(req: VibeCheckRequest) -> VibeCheckResponse:
    refs = await _refs()
    idx = {r.source: r for r in refs}
    checklists: List[ChecklistItem] = []

    # LinkedIn checklist
    checklists.append(
        ChecklistItem(
            id="linkedin_weekly",
            text=(
                "Publish one native document or carousel weekly; avoid outbound links in body; add industry expertise keywords;"
                " reply to 5 relevant posts with 15+ word comments (meaningful conversation signal)."
            ),
            rationale="LinkedIn surfaces relevant, expertise-driven, meaningful comments — native formats perform well.",
            refs=[idx.get(LINKEDIN), idx.get(INSIDER)] if idx.get(LINKEDIN) else refs[:1],
        )
    )

    # Instagram checklist
    checklists.append(
        ChecklistItem(
            id="instagram_weekly",
            text=(
                "Optimize captions for search; add location; post 1 Feed + 1 Reel; include a DM-share hook (‘send to a friend who…’)."
            ),
            rationale="Ranking leans on activity, post info, relationships; DM shares are strong signals.",
            refs=[idx.get(SMT), idx.get(INSIDER)] if idx.get(SMT) else refs[:1],
        )
    )

    # YouTube checklist
    checklists.append(
        ChecklistItem(
            id="youtube_weekly",
            text=(
                "Target >3% CTR thumbnails; optimize first 30s retention; pair Shorts with long-form + Community post;"
                " focus on satisfaction and history over tags."
            ),
            rationale="Recommendations optimize for predicted satisfaction using watch/search history.",
            refs=[idx.get(YTPOLARIS), idx.get(YOUTUBE_BLOG)] if idx.get(YTPOLARIS) else refs[:1],
        )
    )

    nudges = [
        "LinkedIn: Missing native document this week. Draft now. Avoid outbound link in body.",
        "Instagram: Encourage DM shares on this reel. Add a ‘send to a friend who…’ CTA.",
    ]

    kpis = [
        "Post-level saves",
        "Comments over likes ratio",
        "YT watch time per impression",
        "Session starts from channel page",
        "Instagram DM shares",
    ]

    return VibeCheckResponse(checklists=checklists, nudges=nudges, kpis=kpis)

