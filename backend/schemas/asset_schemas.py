from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl


class MemeRequest(BaseModel):
    topic: str
    audience: str = "general"
    style: Literal["relatable", "sarcastic", "wholesome", "absurd"] = "relatable"
    tone: str = "playful"
    language: str = "en"
    seed_image_url: Optional[HttpUrl] = None


class MemeResponse(BaseModel):
    template_name: str
    top_text: str
    bottom_text: str
    alt_text: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)


class CarouselRequest(BaseModel):
    topic: str
    audience: str = "general"
    slides_count: int = Field(7, ge=3, le=12)
    call_to_action: str = "Order now"
    language: str = "en"
    tone: str = "helpful"


class CarouselSlide(BaseModel):
    heading: str
    bullets: List[str] = Field(default_factory=list)


class CarouselResponse(BaseModel):
    slides: List[CarouselSlide]
    caption: str
    hashtags: List[str] = Field(default_factory=list)


class ShortVideoRequest(BaseModel):
    topic: str
    platform: Literal["instagram", "tiktok", "youtube_shorts"] = "instagram"
    duration_seconds: int = Field(30, ge=8, le=60)
    language: str = "en"
    tone: str = "energetic"


class VideoBeat(BaseModel):
    t: float = Field(description="time offset seconds")
    action: str
    on_screen_text: str = ""


class ShortVideoResponse(BaseModel):
    hook: str
    beats: List[VideoBeat] = Field(default_factory=list)
    voiceover_script: str
    caption: str
    hashtags: List[str] = Field(default_factory=list)


class SupervisorRequest(BaseModel):
    topic: str
    audience: str = "general"
    asset_types: List[Literal["meme", "carousel", "short_video", "ad_copy", "image_prompt", "thread"]] = Field(default_factory=lambda: ["meme", "carousel"]) 
    research: bool = True
    language: str = "en"
    tone: str = "friendly"


class SupervisorResponse(BaseModel):
    topic: str
    research_summary: Optional[str] = None
    meme: Optional[MemeResponse] = None
    carousel: Optional[CarouselResponse] = None
    short_video: Optional[ShortVideoResponse] = None
    ad_copy: Optional["AdCopyResponse"] = None
    image_prompt: Optional["ImagePromptResponse"] = None
    thread: Optional["ThreadResponse"] = None


class AdCopyRequest(BaseModel):
    product_summary: str
    platforms: List[Literal["facebook", "instagram", "linkedin", "google_search"]] = Field(default_factory=lambda: ["facebook", "instagram"]) 
    offer: str = ""
    call_to_action: str = "Order now"
    language: str = "en"
    tone: str = "friendly"


class AdVariant(BaseModel):
    platform: str
    primary_text: str
    headline: str
    description: str = ""


class AdCopyResponse(BaseModel):
    variants: List[AdVariant]


class ImagePromptRequest(BaseModel):
    concept: str
    style: str = Field("cinematic", description="visual style tag, e.g., 'flat illustration', 'studio photography'")
    brand_palette: List[str] = Field(default_factory=list, description="hex colors or descriptors")
    language: str = "en"


class ImagePromptResponse(BaseModel):
    stable_diffusion_prompt: str
    dalle_prompt: str
    negative_prompt: str = ""
    composition_notes: str = ""


class ThreadRequest(BaseModel):
    topic: str
    platform: Literal["twitter", "threads"] = "twitter"
    posts: int = Field(8, ge=3, le=20)
    language: str = "en"
    tone: str = "insightful"


class ThreadResponse(BaseModel):
    platform: str
    items: List[str]


# Additional asset agents (headline, tagline, hashtags, email, sms, push, blog outline, press release, WhatsApp)

class HeadlineRequest(BaseModel):
    topic: str
    tone: str = "friendly"
    language: str = "en"
    count: int = Field(8, ge=3, le=20)


class HeadlineResponse(BaseModel):
    headlines: List[str]


class TaglineRequest(BaseModel):
    product_summary: str
    tone: str = "bold"
    language: str = "en"
    count: int = Field(10, ge=3, le=30)


class TaglineResponse(BaseModel):
    taglines: List[str]


class HashtagRequest(BaseModel):
    topic: str
    platform: Literal["instagram", "twitter", "tiktok", "linkedin"] = "instagram"
    language: str = "en"
    count: int = Field(20, ge=5, le=50)


class HashtagResponse(BaseModel):
    hashtags: List[str]


class EmailRequest(BaseModel):
    product_summary: str
    audience: str = "general"
    offer: str = ""
    language: str = "en"
    tone: str = "friendly"


class EmailResponse(BaseModel):
    subject: str
    preheader: str
    body_html: str


class SMSRequest(BaseModel):
    offer: str
    language: str = "en"
    tone: str = "direct"
    count: int = Field(5, ge=3, le=15)


class SMSResponse(BaseModel):
    variants: List[str]


class PushRequest(BaseModel):
    message_purpose: str
    channel: Literal["web", "app"] = "web"
    language: str = "en"
    tone: str = "urgent"


class PushResponse(BaseModel):
    title: str
    body: str
    cta: str


class BlogOutlineRequest(BaseModel):
    topic: str
    audience: str = "general"
    language: str = "en"
    tone: str = "authoritative"


class BlogSection(BaseModel):
    heading: str
    bullets: List[str] = Field(default_factory=list)


class BlogOutlineResponse(BaseModel):
    title: str
    sections: List[BlogSection]


class PressReleaseRequest(BaseModel):
    company: str
    announcement: str
    date_str: str = Field("", description="e.g., 2025-09-01")
    quotes: List[str] = Field(default_factory=list)
    language: str = "en"


class PressReleaseResponse(BaseModel):
    headline: str
    subheadline: str
    body: str


class WhatsAppRequest(BaseModel):
    campaign_goal: str
    offer: str = ""
    language: str = "en"
    tone: str = "friendly"
    count: int = Field(5, ge=3, le=15)


class WhatsAppResponse(BaseModel):
    messages: List[str]


# 10 more specialized asset agents

class PollItem(BaseModel):
    question: str
    options: List[str] = Field(default_factory=list)


class PollRequest(BaseModel):
    topic: str
    platform: Literal["instagram", "twitter", "linkedin", "youtube"] = "instagram"
    language: str = "en"
    count: int = Field(5, ge=2, le=20)


class PollResponse(BaseModel):
    polls: List[PollItem]


class GiveawayRequest(BaseModel):
    goal: str
    prize: str
    platform: Literal["instagram", "twitter", "linkedin", "facebook"] = "instagram"
    language: str = "en"
    tone: str = "excited"


class GiveawayResponse(BaseModel):
    announcement: str
    rules: List[str] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    hashtags: List[str] = Field(default_factory=list)


class TestimonialRequest(BaseModel):
    product_summary: str
    personas: List[str] = Field(default_factory=list)
    language: str = "en"
    tone: str = "authentic"
    count: int = Field(3, ge=1, le=10)


class TestimonialResponse(BaseModel):
    quotes: List[str]


class DripEmail(BaseModel):
    day_offset: int
    subject: str
    outline: List[str] = Field(default_factory=list)


class DripCampaignRequest(BaseModel):
    goal: str
    emails_count: int = Field(5, ge=3, le=12)
    cadence_days: int = Field(2, ge=1, le=14)
    language: str = "en"
    tone: str = "helpful"


class DripCampaignResponse(BaseModel):
    emails: List[DripEmail]


class CtaRequest(BaseModel):
    context: str
    language: str = "en"
    tone: str = "direct"
    count: int = Field(12, ge=3, le=40)


class CtaResponse(BaseModel):
    ctas: List[str]


class HookRequest(BaseModel):
    topic: str
    language: str = "en"
    tone: str = "provocative"
    count: int = Field(15, ge=5, le=50)


class HookResponse(BaseModel):
    hooks: List[str]


class CaptionRequest(BaseModel):
    topic: str
    platform: Literal["instagram", "linkedin", "twitter", "facebook", "tiktok"] = "instagram"
    language: str = "en"
    tone: str = "friendly"
    count: int = Field(10, ge=3, le=40)


class CaptionResponse(BaseModel):
    captions: List[str]


class NewsletterSection(BaseModel):
    heading: str
    bullets: List[str] = Field(default_factory=list)


class NewsletterRequest(BaseModel):
    topic: str
    sections: int = Field(5, ge=3, le=10)
    language: str = "en"
    tone: str = "informative"


class NewsletterResponse(BaseModel):
    title: str
    sections: List[NewsletterSection]


class PersonaAngleItem(BaseModel):
    persona: str
    angle: str
    examples: List[str] = Field(default_factory=list)


class PersonaAngleRequest(BaseModel):
    topic: str
    personas: List[str]
    language: str = "en"
    tone: str = "insightful"


class PersonaAngleResponse(BaseModel):
    items: List[PersonaAngleItem]


class CaseStudySection(BaseModel):
    heading: str
    bullets: List[str] = Field(default_factory=list)


class CaseStudyOutlineRequest(BaseModel):
    client: str
    challenge: str
    solution: str
    results: str
    language: str = "en"


class CaseStudyOutlineResponse(BaseModel):
    title: str
    sections: List[CaseStudySection]
