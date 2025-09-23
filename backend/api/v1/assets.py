from fastapi import APIRouter, HTTPException

from agents.meme_agent import run_meme
from agents.carousel_agent import run_carousel
from agents.short_video_agent import run_short_video
from agents.asset_supervisor_agent import run_asset_supervisor
from agents.ad_copy_agent import run_ad_copy
from agents.headline_agent import run_headline
from agents.tagline_agent import run_tagline
from agents.hashtag_agent import run_hashtag
from agents.email_agent import run_email
from agents.sms_agent import run_sms
from agents.push_agent import run_push
from agents.blog_outline_agent import run_blog_outline
from agents.press_release_agent import run_press_release
from agents.whatsapp_agent import run_whatsapp
from agents.image_prompt_agent import run_image_prompt
from agents.thread_agent import run_thread
from agents.poll_agent import run_poll
from agents.giveaway_agent import run_giveaway
from agents.testimonial_agent import run_testimonial
from agents.drip_campaign_agent import run_drip_campaign
from agents.cta_agent import run_cta
from agents.hook_agent import run_hook
from agents.caption_agent import run_caption
from agents.newsletter_agent import run_newsletter
from agents.persona_angle_agent import run_persona_angle
from agents.case_study_outline_agent import run_case_study_outline
from schemas.asset_schemas import (
    MemeRequest, MemeResponse,
    CarouselRequest, CarouselResponse,
    ShortVideoRequest, ShortVideoResponse,
    SupervisorRequest, SupervisorResponse,
    HeadlineRequest, HeadlineResponse,
    TaglineRequest, TaglineResponse,
    HashtagRequest, HashtagResponse,
    EmailRequest, EmailResponse,
    SMSRequest, SMSResponse,
    PushRequest, PushResponse,
    BlogOutlineRequest, BlogOutlineResponse,
    PressReleaseRequest, PressReleaseResponse,
    WhatsAppRequest, WhatsAppResponse,
    ImagePromptRequest, ImagePromptResponse,
    ThreadRequest, ThreadResponse,
    PollRequest, PollResponse,
    GiveawayRequest, GiveawayResponse,
    TestimonialRequest, TestimonialResponse,
    DripCampaignRequest, DripCampaignResponse,
    CtaRequest, CtaResponse,
    HookRequest, HookResponse,
    CaptionRequest, CaptionResponse,
    NewsletterRequest, NewsletterResponse,
    PersonaAngleRequest, PersonaAngleResponse,
    CaseStudyOutlineRequest, CaseStudyOutlineResponse,
    AdCopyRequest, AdCopyResponse,
)


router = APIRouter()


@router.post("/meme", response_model=MemeResponse)
async def create_meme(req: MemeRequest):
    try:
        result = await run_meme(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected meme error: {e}")


@router.post("/carousel", response_model=CarouselResponse)
async def create_carousel(req: CarouselRequest):
    try:
        result = await run_carousel(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected carousel error: {e}")


@router.post("/short-video", response_model=ShortVideoResponse)
async def create_short_video(req: ShortVideoRequest):
    try:
        result = await run_short_video(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected short video error: {e}")


@router.post("/supervisor", response_model=SupervisorResponse)
async def asset_supervisor(req: SupervisorRequest):
    try:
        result = await run_asset_supervisor(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected supervisor error: {e}")


@router.post("/ad-copy", response_model=AdCopyResponse)
async def create_ad_copy(req: AdCopyRequest):
    try:
        result = await run_ad_copy(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected ad copy error: {e}")


@router.post("/headline", response_model=HeadlineResponse)
async def create_headlines(req: HeadlineRequest):
    try:
        result = await run_headline(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected headline error: {e}")


@router.post("/tagline", response_model=TaglineResponse)
async def create_taglines(req: TaglineRequest):
    try:
        result = await run_tagline(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected tagline error: {e}")


@router.post("/hashtags", response_model=HashtagResponse)
async def create_hashtags(req: HashtagRequest):
    try:
        result = await run_hashtag(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected hashtags error: {e}")


@router.post("/email", response_model=EmailResponse)
async def create_email(req: EmailRequest):
    try:
        result = await run_email(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected email error: {e}")


@router.post("/sms", response_model=SMSResponse)
async def create_sms(req: SMSRequest):
    try:
        result = await run_sms(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected sms error: {e}")


@router.post("/push", response_model=PushResponse)
async def create_push(req: PushRequest):
    try:
        result = await run_push(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected push error: {e}")


@router.post("/blog-outline", response_model=BlogOutlineResponse)
async def create_blog_outline(req: BlogOutlineRequest):
    try:
        result = await run_blog_outline(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected blog outline error: {e}")


@router.post("/press-release", response_model=PressReleaseResponse)
async def create_press_release(req: PressReleaseRequest):
    try:
        result = await run_press_release(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected press release error: {e}")


@router.post("/whatsapp", response_model=WhatsAppResponse)
async def create_whatsapp(req: WhatsAppRequest):
    try:
        result = await run_whatsapp(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected WhatsApp error: {e}")


@router.post("/image-prompt", response_model=ImagePromptResponse)
async def create_image_prompt(req: ImagePromptRequest):
    try:
        result = await run_image_prompt(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected image prompt error: {e}")


@router.post("/thread", response_model=ThreadResponse)
async def create_thread(req: ThreadRequest):
    try:
        result = await run_thread(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected thread error: {e}")


@router.post("/polls", response_model=PollResponse)
async def create_polls(req: PollRequest):
    try:
        result = await run_poll(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected polls error: {e}")


@router.post("/giveaway", response_model=GiveawayResponse)
async def create_giveaway(req: GiveawayRequest):
    try:
        result = await run_giveaway(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected giveaway error: {e}")


@router.post("/testimonials", response_model=TestimonialResponse)
async def create_testimonials(req: TestimonialRequest):
    try:
        result = await run_testimonial(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected testimonials error: {e}")


@router.post("/drip-campaign", response_model=DripCampaignResponse)
async def create_drip_campaign(req: DripCampaignRequest):
    try:
        result = await run_drip_campaign(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected drip campaign error: {e}")


@router.post("/cta", response_model=CtaResponse)
async def create_ctas(req: CtaRequest):
    try:
        result = await run_cta(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected CTA error: {e}")


@router.post("/hooks", response_model=HookResponse)
async def create_hooks(req: HookRequest):
    try:
        result = await run_hook(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected hooks error: {e}")


@router.post("/captions", response_model=CaptionResponse)
async def create_captions(req: CaptionRequest):
    try:
        result = await run_caption(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected captions error: {e}")


@router.post("/newsletter", response_model=NewsletterResponse)
async def create_newsletter(req: NewsletterRequest):
    try:
        result = await run_newsletter(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected newsletter error: {e}")


@router.post("/persona-angles", response_model=PersonaAngleResponse)
async def create_persona_angles(req: PersonaAngleRequest):
    try:
        result = await run_persona_angle(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected persona angles error: {e}")


@router.post("/case-study-outline", response_model=CaseStudyOutlineResponse)
async def create_case_study_outline(req: CaseStudyOutlineRequest):
    try:
        result = await run_case_study_outline(req.model_dump())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected case study outline error: {e}")
