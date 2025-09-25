from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional
import os

from langchain_ollama.chat_models import ChatOllama
from langchain_ollama.embeddings import OllamaEmbeddings

from core.config import settings
from .google_maps_service import GoogleMapsService
from .web_scraper_service import WebScraperService
from .search_service import SearchService
from .summarization_service import SummarizationService
from .moderation_service import ModerationService
from .keywords_service import KeywordService
from .link_preview_service import LinkPreviewService
from .pdf_service import PDFService
from .youtube_service import YouTubeService
from .rss_service import RSSService
from .embedding_service import EmbeddingService
from .crawl_service import CrawlService
from .translation_service import TranslationService
from .tone_service import ToneService
from .ner_service import NERService
from .topic_cluster_service import TopicClusterService
from .social_service import SocialService
from .twitter_x_service import TwitterXService
from .linkedin_service import LinkedInService
from .reddit_service import RedditService
from .hackernews_service import HackerNewsService
from .youtube_search_service import YouTubeSearchService
from .instagram_service import InstagramService
from .tiktok_service import TikTokService
from .quora_service import QuoraService
from .facebook_service import FacebookService
from .threads_service import ThreadsService
from .mastodon_service import MastodonService
from .medium_service import MediumService
from .producthunt_service import ProductHuntService
from .substack_service import SubstackService
from .pinterest_service import PinterestService
from .stackoverflow_service import StackOverflowService
from .news_service import NewsService
from .wikipedia_service import WikipediaService
from .canva_service import CanvaService
from .oauth_service import OAuthService
from .user_store_service import UserStoreService
from .google_sheets_service import GoogleSheetsService
from .google_docs_service import GoogleDocsService
from .google_forms_service import GoogleFormsService
from .google_calendar_service import GoogleCalendarService
from .gmail_service import GmailService
from .youtube_data_service import YouTubeDataService
from .ga4_service import GA4Service
from .notion_service import NotionService
from .discord_service import DiscordService
from .instrumentation_service import InstrumentationService
from .connector_manager import ConnectorManager
from .calendar_sync_service import CalendarSyncService


logger = logging.getLogger(__name__)


@dataclass
class Services:
    maps: GoogleMapsService
    search: SearchService
    scraper: WebScraperService
    summarizer: SummarizationService
    moderation: ModerationService
    keywords: KeywordService
    link_preview: LinkPreviewService
    pdf: PDFService
    youtube: YouTubeService
    rss: RSSService
    embedder: EmbeddingService
    crawler: CrawlService
    translate: TranslationService
    tone: ToneService
    ner: NERService
    topic_cluster: TopicClusterService
    social: SocialService
    twitter: TwitterXService
    linkedin: LinkedInService
    reddit: RedditService
    hackernews: HackerNewsService
    youtube_search: YouTubeSearchService
    instagram: InstagramService
    tiktok: TikTokService
    quora: QuoraService
    facebook: FacebookService
    threads: ThreadsService
    mastodon: MastodonService
    medium: MediumService
    producthunt: ProductHuntService
    substack: SubstackService
    pinterest: PinterestService
    stackoverflow: StackOverflowService
    news: NewsService
    wikipedia: WikipediaService
    canva: CanvaService
    oauth: OAuthService
    users: UserStoreService
    sheets: GoogleSheetsService
    gdocs: GoogleDocsService
    gforms: GoogleFormsService
    gcal: GoogleCalendarService
    gmail: GmailService
    ytd: YouTubeDataService
    ga4: GA4Service
    notion: NotionService
    discord: DiscordService
    metrics: InstrumentationService
    connectors: ConnectorManager
    calendar_sync: CalendarSyncService
    llm_fast: ChatOllama
    llm_reasoning: ChatOllama
    embeddings: OllamaEmbeddings
    vectorstore: Optional[object]


_services: Optional[Services] = None


def init_services() -> Services:
    global _services
    if _services is not None:
        return _services

    logger.info("[services] ▶ initializing shared services …")

    # Core clients
    maps = GoogleMapsService()
    search = SearchService()
    scraper = WebScraperService()

    # LLMs
    llm_fast = ChatOllama(
        model=settings.OLLAMA_FAST_MODEL,
        temperature=0.3,
        base_url=settings.OLLAMA_BASE_URL,
    )
    llm_reasoning = ChatOllama(
        model=settings.OLLAMA_REASONING_MODEL,
        temperature=0.3,
        base_url=settings.OLLAMA_BASE_URL,
    )

    # Utility services powered by LLM
    summarizer = SummarizationService(llm_reasoning)
    moderation = ModerationService(llm_reasoning)
    keywords = KeywordService(llm_fast)
    link_preview = LinkPreviewService(scraper)
    pdf = PDFService()
    youtube = YouTubeService()
    rss = RSSService()

    # Embeddings + vector store (best-effort)
    embeddings = OllamaEmbeddings(model=settings.OLLAMA_EMBEDDINGS_MODEL, base_url=settings.OLLAMA_BASE_URL)
    embedder = EmbeddingService(embeddings)
    translate = TranslationService(llm_fast)
    tone = ToneService(llm_reasoning)
    ner = NERService(llm_fast)
    topic_cluster = TopicClusterService(embedder)
    social = SocialService(search)
    twitter = social.twitter
    linkedin = social.linkedin
    reddit = RedditService(search)
    hackernews = HackerNewsService()
    youtube_search = YouTubeSearchService()
    instagram = InstagramService(search)
    tiktok = TikTokService(search)
    quora = QuoraService(search)
    facebook = FacebookService(search)
    threads = ThreadsService(search)
    mastodon = MastodonService(search)
    medium = MediumService(search)
    producthunt = ProductHuntService(search)
    substack = SubstackService(search)
    pinterest = PinterestService(search)
    stackoverflow = StackOverflowService(search)
    news = NewsService()
    wikipedia = WikipediaService()
    canva = CanvaService(llm_reasoning)
    oauth = OAuthService()
    users = UserStoreService()
    # Metrics + managers
    metrics = InstrumentationService()
    connectors = ConnectorManager(metrics)
    # Connectors
    sheets = GoogleSheetsService(oauth)
    gdocs = GoogleDocsService(oauth)
    gforms = GoogleFormsService(oauth)
    gcal = GoogleCalendarService(oauth)
    gmail = GmailService(oauth)
    ytd = YouTubeDataService(oauth)
    ga4 = GA4Service(oauth)
    notion = NotionService(oauth)
    discord = DiscordService(bot_token=os.getenv('DISCORD_BOT_TOKEN'))
    calendar_sync = CalendarSyncService(gcal)
    vectorstore = None  # ChromaDB disabled

    _services = Services(
        maps=maps,
        search=search,
        scraper=scraper,
        llm_fast=llm_fast,
        llm_reasoning=llm_reasoning,
        summarizer=summarizer,
        moderation=moderation,
        keywords=keywords,
        link_preview=link_preview,
        pdf=pdf,
        youtube=youtube,
        rss=rss,
        embedder=embedder,
        crawler=CrawlService(scraper),
        embeddings=embeddings,
        vectorstore=vectorstore,
        translate=translate,
        tone=tone,
        ner=ner,
        topic_cluster=topic_cluster,
        social=social,
        twitter=twitter,
        linkedin=linkedin,
        reddit=reddit,
        hackernews=hackernews,
        youtube_search=youtube_search,
        instagram=instagram,
        tiktok=tiktok,
        quora=quora,
        facebook=facebook,
        threads=threads,
        mastodon=mastodon,
        medium=medium,
        producthunt=producthunt,
        substack=substack,
        pinterest=pinterest,
        stackoverflow=stackoverflow,
        news=news,
        wikipedia=wikipedia,
        canva=canva,
        oauth=oauth,
        users=users,
        sheets=sheets,
        gdocs=gdocs,
        gforms=gforms,
        gcal=gcal,
        gmail=gmail,
        ytd=ytd,
        ga4=ga4,
        notion=notion,
        discord=discord,
        metrics=metrics,
        connectors=connectors,
        calendar_sync=calendar_sync,
    )
    logger.info("[services] ✅ initialized shared services")
    return _services


def get_services() -> Services:
    return init_services()


async def shutdown_services() -> None:
    global _services
    if _services is None:
        return
    logger.info("[services] ▶ shutting down shared services …")
    try:
        await _services.scraper.close()
    except Exception:
        pass
    _services = None
    logger.info("[services] ✅ shutdown complete")
