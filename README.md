# Geo-Strategist AI Technical Manual

Version 1.2.0. Geo-Strategist AI is a local-first strategic marketing engine that combines a 
FastAPI backend, LangGraph-powered agents, and a modular service registry. This manual documents
 product capabilities, operational procedures, and extension workflows across the entire stack.

## Table of Contents

- 1. Vision and Principles
- 2. Platform Topology
- 3. Dependency Matrix
- 4. Quick Start
- 5. Environment Configuration
- 6. Runtime Lifecycle
- 7. Agent Directory
- 8. Multi-Agent Workflows
- 9. Service Registry
- 10. Schema Library
- 11. API Surface
- 12. Frontend and UX
- 13. Developer Tooling
- 14. Observability
- 15. Security
- 16. Extension Recipes
- 17. Testing Strategy
- 18. Deployment Playbooks
- 19. Troubleshooting
- 20. Glossary
- 21. Operational Checklists
- Appendix A. Environment Variables
- Appendix B. Agent-Service Map

## Vision and Principles

The platform is engineered for marketing strategists who require transparent, reproducible AI 
assistance. Core principles guide design decisions:

- Local-first execution: all LLM calls flow through Ollama so sensitive briefs stay on your machine.
- Explicit contracts: every payload is backed by Pydantic schemas to prevent silent prompt drift.
- Composable agents: tasks decompose into shareable LangGraph workflows that can be orchestrated dynamically.
- Graceful degradation: optional integrations fall back to stub behavior when credentials are missing.
- Observability by default: structured logs surface dependency readiness and agent milestones.

## Platform Topology

Geo-Strategist AI ships as a monorepo with clearly separated concerns. Use the following 
cheatsheet when navigating the codebase or planning deployments.

- `backend/`: FastAPI application, agents, schemas, services, and startup wiring.
- `web/`: Vite + React shell prepared for dashboard development with a proxy into the backend.
- `frontend/index.html`: Tailwind-based concept UI demonstrating future layout possibilities.
- `chroma_db/`: On-disk storage for ChromaDB collections when vector search is enabled.
- `start.bat` and `dev.ps1`: Windows convenience scripts to spin up local environments quickly.

## Dependency Matrix

The backend depends on a concise set of runtime services. Ensure the following components are 
available during development:

- Python 3.10+ with the dependencies listed in `backend/requirements.txt`.
- Node.js 18+ for frontend scaffolding in `web/`.
- Ollama running locally with fast, reasoning, and embedding models declared in `.env`.
- Optional ChromaDB server (defaults to `localhost:8001`) for playbook templates and semantic search.
- Optional OAuth credentials (Google, Canva, Discord, Notion) for external integrations.

## Quick Start

Use these workflows to launch the stack on Windows. Recommend verifying dependencies before each
 run.

- One-click: execute `start.bat` to install missing npm packages, launch FastAPI, spawn ChromaDB, and open the Vite UI.
- Backend manual: `cd backend`, create `.venv`, install requirements, run `python main.py`.
- Frontend manual: `cd web`, `npm install`, then `npm run dev` to serve the React shell on port 5173.
- ChromaDB manual: `chroma run --path ./chroma_db --host 0.0.0.0 --port 8001` to enable embeddings.
- Verification: browse `http://localhost:8000/docs` for Swagger UI and `http://localhost:5173` for the Vite shell.

## Environment Configuration

Geo-Strategist loads configuration from two `.env` files. Copy the examples to configure secrets
 and runtime toggles.

### Root `.env.example`

- `PUBLIC_BASE_URL` = `http://localhost:8000`
- `CHROMA_HOST` = `localhost`
- `CHROMA_PORT` = `8001`
- `OLLAMA_HOST` = `localhost`
- `OLLAMA_PORT` = `11434`
- `OLLAMA_FAST_MODEL` = `gemma3:1b`
- `OLLAMA_REASONING_MODEL` = `gemma3:4b`
- `OLLAMA_EMBEDDINGS_MODEL` = `nomic-embed-text`
- `GOOGLE_MAPS_API_KEY` = `your_maps_key`
- `GOOGLE_MAPS_BROWSER_API_KEY` = `your_browser_key`
- `EXPOSE_SERVER_MAPS_KEY_TO_FRONTEND` = `0`
- `GOOGLE_CLIENT_ID` = `your_google_client_id`
- `GOOGLE_CLIENT_SECRET` = `your_google_client_secret`
- `NOTION_CLIENT_ID` = ``
- `NOTION_CLIENT_SECRET` = ``
- `NOTION_OAUTH_AUTH_URL` = `https://api.notion.com/v1/oauth/authorize`
- `NOTION_OAUTH_TOKEN_URL` = `https://api.notion.com/v1/oauth/token`
- `DISCORD_CLIENT_ID` = ``
- `DISCORD_CLIENT_SECRET` = ``
- `DISCORD_BOT_TOKEN` = ``
- `CANVA_CLIENT_ID` = `your_canva_client_id`
- `CANVA_CLIENT_SECRET` = `your_canva_client_secret`
- `OAUTH_CANVA_AUTH_URL` = `https://example.canva.auth/authorize`
- `OAUTH_CANVA_TOKEN_URL` = `https://example.canva.auth/token`
- `CANVA_SCOPES` = ``
- `CANVA_TEMPLATE_URL` = ``
- `CANVA_BRAND_COLORS` = `#6420FF,#111111,#FFFFFF`
- `SMTP_HOST` = `smtp.example.com`
- `SMTP_PORT` = `587`
- `SMTP_USER` = `me@example.com`
- `SMTP_PASS` = `app_password`
- `SMTP_TLS` = `1`
- `TWITTER_BEARER_TOKEN` = ``
- `X_BEARER_TOKEN` = ``
- `REDDIT_CLIENT_ID` = ``
- `REDDIT_CLIENT_SECRET` = ``
- `REDDIT_USER_AGENT` = `geo-strategist/1.0`
- `YOUTUBE_API_KEY` = ``
- `TRELLO_API_KEY` = ``
- `TRELLO_API_TOKEN` = ``
- `SENDGRID_API_KEY` = ``
- `UNSPLASH_ACCESS_KEY` = ``
- `SKIP_BOOTSTRAP` = `0`

### Backend `.env.example`

- `PUBLIC_BASE_URL` = `http://localhost:8000`
- `CHROMA_HOST` = `localhost`
- `CHROMA_PORT` = `8001`
- `OLLAMA_HOST` = `localhost`
- `OLLAMA_PORT` = `11434`
- `OLLAMA_FAST_MODEL` = `gemma3:1b`
- `OLLAMA_REASONING_MODEL` = `gemma3:4b`
- `OLLAMA_EMBEDDINGS_MODEL` = `jina-embeddings-v2-base-en`
- `GOOGLE_MAPS_API_KEY` = `your_maps_key`
- `GOOGLE_MAPS_BROWSER_API_KEY` = `your_browser_key`
- `EXPOSE_SERVER_MAPS_KEY_TO_FRONTEND` = `0`
- `GOOGLE_CLIENT_ID` = ``
- `GOOGLE_CLIENT_SECRET` = ``
- `NOTION_CLIENT_ID` = ``
- `NOTION_CLIENT_SECRET` = ``
- `NOTION_OAUTH_AUTH_URL` = `https://api.notion.com/v1/oauth/authorize`
- `NOTION_OAUTH_TOKEN_URL` = `https://api.notion.com/v1/oauth/token`
- `DISCORD_CLIENT_ID` = ``
- `DISCORD_CLIENT_SECRET` = ``
- `DISCORD_BOT_TOKEN` = ``
- `CANVA_CLIENT_ID` = ``
- `CANVA_CLIENT_SECRET` = ``
- `OAUTH_CANVA_AUTH_URL` = ``
- `OAUTH_CANVA_TOKEN_URL` = ``
- `CANVA_SCOPES` = ``
- `REDDIT_CLIENT_ID` = ``
- `REDDIT_CLIENT_SECRET` = ``
- `REDDIT_USER_AGENT` = `geo-strategist/1.0`
- `YOUTUBE_API_KEY` = ``
- `TRELLO_API_KEY` = ``
- `TRELLO_API_TOKEN` = ``
- `SENDGRID_API_KEY` = ``
- `UNSPLASH_ACCESS_KEY` = ``
- `SKIP_BOOTSTRAP` = `0`

Defaults worth highlighting: `PUBLIC_BASE_URL` defaults to `http://localhost:8000`, 
`OLLAMA_EMBEDDINGS_MODEL` defaults to `jina-embeddings-v2-base-en`, and Google Maps keys are 
optional but unlock geo intelligence features.

## Runtime Lifecycle

- Startup: `main.py` mounts routers, sets up CORS, initializes services, and triggers best-effort health checks for Ollama and ChromaDB.
- Service registry: `services.registry.init_services` constructs Ollama chat models, embeddings, connectors, and Google integrations in one pass.
- Request handling: FastAPI routers import agents and schemas, returning JSON responses with consistent error envelopes.
- Shutdown: `shutdown_services` releases shared clients, closing HTTP sessions and background tasks.
- Developer UX: environment variables `AUTO_FRONTEND` and `AUTO_OPEN_BROWSER` control automatic Vite startup and browser launch.

## Agent Directory

Agents are modular LangGraph orchestrations that turn marketing inputs into validated 
deliverables. Each agent exposes a `run_*` entrypoint backed by Pydantic validation and returns 
JSON-ready payloads.

### Agent: Ad Copy Agent

- Path: `backend/agents/ad_copy_agent.py` | Entrypoints: `run_ad_copy` | Schemas: AdCopyRequest, AdCopyResponse, AdVariant
- Service dependencies: get_services, registry | Helper utilities: build_adcopy_graph, draft_ads
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Agent Hub

- Path: `backend/agents/agent_hub.py` | Entrypoints: `run_workflow` | Schemas: AISASRequest, ActionRequest, CashGuardRequest, CashRequest, CompetitorScanRequest, LateralVerticalRequest, LocationRequest, MarketNeedReport, OfferRequest, PermissionRequest, PositioningGenerationRequest, ReframeRequest, SegmentRequest, TaskEvent, WorkflowRequest, WorkflowResult, WoundRequest
- Service dependencies: no shared services | Helper utilities: repl
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Archive Agent

- Path: `backend/agents/archive_agent.py` | Entrypoints: `run_archive_agent`, `run_recommendation_agent` | Schemas: AttributionReport, NextMoveRecommendation, OutcomeCharter, PlaybookTemplate, StrikePlan
- Service dependencies: get_services, registry | Helper utilities: find_relevant_playbooks, get_vectorstore, parameterize_and_summarize, save_playbook_to_archive
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Asset Supervisor Agent

- Path: `backend/agents/asset_supervisor_agent.py` | Entrypoints: `run_asset_supervisor` | Schemas: AdCopyResponse, CarouselResponse, ImagePromptResponse, MemeResponse, ShortVideoResponse, SupervisorRequest, SupervisorResponse, ThreadResponse
- Service dependencies: get_services, registry | Helper utilities: build_supervisor_graph, generate_assets, maybe_research, moderate_assets
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Attribution Agent

- Path: `backend/agents/attribution_agent.py` | Entrypoints: `run_attribution_agent` | Schemas: AttributionEvent, AttributionReport, CampaignSimulationReport, ProofArtifact
- Service dependencies: no shared services | Helper utilities: build_attribution_graph, process_events_and_build_report
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Blog Outline Agent

- Path: `backend/agents/blog_outline_agent.py` | Entrypoints: `run_blog_outline` | Schemas: BlogOutlineRequest, BlogOutlineResponse, BlogSection
- Service dependencies: get_services, registry | Helper utilities: build_blog_graph, draft_outline
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Canva Agent

- Path: `backend/agents/canva_agent.py` | Entrypoints: `run_canva_design` | Schemas: CanvaDesignRequest, CanvaDesignResponse
- Service dependencies: CanvaService, canva_service, get_services, registry | Helper utilities: internal nodes
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Caption Agent

- Path: `backend/agents/caption_agent.py` | Entrypoints: `run_caption` | Schemas: CaptionRequest, CaptionResponse
- Service dependencies: get_services, registry | Helper utilities: build_caption_graph, draft_captions
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Carousel Agent

- Path: `backend/agents/carousel_agent.py` | Entrypoints: `run_carousel` | Schemas: CarouselRequest, CarouselResponse, CarouselSlide
- Service dependencies: get_services, registry | Helper utilities: build_carousel_graph, draft_carousel
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Case Study Outline Agent

- Path: `backend/agents/case_study_outline_agent.py` | Entrypoints: `run_case_study_outline` | Schemas: CaseStudyOutlineRequest, CaseStudyOutlineResponse, CaseStudySection
- Service dependencies: get_services, registry | Helper utilities: build_case_study_graph, draft_case_study
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Chat Orchestrator

- Path: `backend/agents/chat_orchestrator.py` | Entrypoints: `run_chat_orchestrator` | Schemas: ActionLog, Attachment, ChatTurnRequest, ChatTurnResponse
- Service dependencies: build_ics_event, calendar_service, get_services, make_simple_pdf_base64, pdf_writer_service, registry | Helper utilities: emit, stream_chat_events
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Cohort Agent

- Path: `backend/agents/cohort_agent.py` | Entrypoints: `run_cohort_strategist_agent` | Schemas: Cohort, CohortStrategy, CohortStrategyReport, EnrichedCohort, ICPCard, ICPReport
- Service dependencies: get_services, registry | Helper utilities: build_cohort_strategist_graph, enrich_single_cohort, generate_cohort_strategies
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Competitor Intel Agent

- Path: `backend/agents/competitor_intel_agent.py` | Entrypoints: `run_competitor_scan` | Schemas: CompetitorCard, CompetitorScanRequest, CompetitorScanResponse, CompetitorSignal
- Service dependencies: get_services, registry | Helper utilities: build_competitor_intel_graph, collect_candidates, draft_cards, enrich_candidates
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Creative Agent

- Path: `backend/agents/creative_agent.py` | Entrypoints: `run_creative_director_agent` | Schemas: AssetBrief, AssetPackage, CreativeAsset, OutcomeCharter, StrikePlan
- Service dependencies: get_services, registry | Helper utilities: build_creative_director_graph, generate_all_assets, generate_single_asset
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Cta Agent

- Path: `backend/agents/cta_agent.py` | Entrypoints: `run_cta` | Schemas: CtaRequest, CtaResponse
- Service dependencies: get_services, registry | Helper utilities: build_cta_graph, draft_ctas
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Deep Research Agent

- Path: `backend/agents/deep_research_agent.py` | Entrypoints: `run_deep_research` | Schemas: ResearchFinding, ResearchRequest, ResearchResponse, SourceNote
- Service dependencies: get_services, registry | Helper utilities: build_research_graph, fetch_pages, note_pages, plan_research, search_web, synthesize
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Drip Campaign Agent

- Path: `backend/agents/drip_campaign_agent.py` | Entrypoints: `run_drip_campaign` | Schemas: DripCampaignRequest, DripCampaignResponse, DripEmail
- Service dependencies: get_services, registry | Helper utilities: build_drip_graph, draft_drip
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Dynamic Intake Agent

- Path: `backend/agents/dynamic_intake_agent.py` | Entrypoints: `run_dynamic_intake_turn` | Schemas: DynamicTurnResponse, IntakeHints, PermissionLadderRequest, PersonaLabel, PersonaProfile
- Service dependencies: get_services, registry | Helper utilities: choose_next_slot, classify_persona, compute_missing_slots, extract_gate_a
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Email Agent

- Path: `backend/agents/email_agent.py` | Entrypoints: `run_email` | Schemas: EmailRequest, EmailResponse
- Service dependencies: get_services, registry | Helper utilities: build_email_graph, draft_email
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Evidence Linker Agent

- Path: `backend/agents/evidence_linker_agent.py` | Entrypoints: `run_copy_evidence_audit` | Schemas: ClaimEvidence, ClaimItem, CopyAuditRequest, CopyAuditResponse, EvidenceItem, RewriteOption
- Service dependencies: get_services, registry | Helper utilities: assess_support, build_evidence_graph, extract_claims, gather_evidence, suggest_rewrites
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Founder Brand Agent

- Path: `backend/agents/founder_brand_agent.py` | Entrypoints: none | Schemas: BrandVoice, FounderBrandCodex, FounderBrandInput, FounderBrandResponse, MeasurementTier
- Service dependencies: no shared services | Helper utilities: generate_codex
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Giveaway Agent

- Path: `backend/agents/giveaway_agent.py` | Entrypoints: `run_giveaway` | Schemas: GiveawayRequest, GiveawayResponse
- Service dependencies: get_services, registry | Helper utilities: build_giveaway_graph, draft_giveaway
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Google Forms Agent

- Path: `backend/agents/google_forms_agent.py` | Entrypoints: none | Schemas: Asset
- Service dependencies: get_services, registry | Helper utilities: create_simple_form, fetch_form_responses
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Hashtag Agent

- Path: `backend/agents/hashtag_agent.py` | Entrypoints: `run_hashtag` | Schemas: HashtagRequest, HashtagResponse
- Service dependencies: get_services, registry | Helper utilities: build_hashtag_graph, draft_hashtags
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Headline Agent

- Path: `backend/agents/headline_agent.py` | Entrypoints: `run_headline` | Schemas: HeadlineRequest, HeadlineResponse
- Service dependencies: get_services, registry | Helper utilities: build_headline_graph, draft_headlines
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Hook Agent

- Path: `backend/agents/hook_agent.py` | Entrypoints: `run_hook` | Schemas: HookRequest, HookResponse
- Service dependencies: get_services, registry | Helper utilities: build_hook_graph, draft_hooks
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Icp Builder Agent

- Path: `backend/agents/icp_builder_agent.py` | Entrypoints: `run_icp_builder_agent` | Schemas: Cohort, GeoSignal, ICPCard, ICPReport, MarketNeedReport
- Service dependencies: get_services, registry | Helper utilities: build_icp_builder_graph, generate_icps_and_cohorts
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Image Prompt Agent

- Path: `backend/agents/image_prompt_agent.py` | Entrypoints: `run_image_prompt` | Schemas: ImagePromptRequest, ImagePromptResponse
- Service dependencies: get_services, registry | Helper utilities: build_image_prompt_graph, draft_image_prompt
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Intake Agent

- Path: `backend/agents/intake_agent.py` | Entrypoints: `run_intake_agent_turn` | Schemas: IntakeState
- Service dependencies: get_services, registry | Helper utilities: build_intake_agent_graph, classify_user_intent, select_next_question
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Landing Page Agent

- Path: `backend/agents/landing_page_agent.py` | Entrypoints: `run_landing_page` | Schemas: FAQItem, HeroSection, LandingPageBlueprint, LandingPageRequest, LandingPageResponse, PageSection
- Service dependencies: get_services, registry | Helper utilities: build_landing_graph, draft_blueprint, gather_reference_notes, moderate_blueprint
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Launch Agent

- Path: `backend/agents/launch_agent.py` | Entrypoints: `run_launch_agent` | Schemas: AssetPackage, Contact, LaunchReport, SchedulePackage, ScheduledJob
- Service dependencies: no shared services | Helper utilities: build_launch_agent_graph, execute_launch_wave, generate_final_report, initialize_campaign, simulate_engagement_and_nurture
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Market Analysis Agent

- Path: `backend/agents/market_analysis_agent.py` | Entrypoints: `run_market_analysis_agent` | Schemas: GeoSignal, MarketNeedReport
- Service dependencies: POI, get_services, google_maps_service, registry | Helper utilities: calculate_scores_and_verdict, calculate_travel_times, geocode_location, scan_for_pois
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Meme Agent

- Path: `backend/agents/meme_agent.py` | Entrypoints: `run_meme` | Schemas: MemeRequest, MemeResponse
- Service dependencies: get_services, registry | Helper utilities: build_meme_graph, draft_meme
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Move Maker Agent

- Path: `backend/agents/move_maker_agent.py` | Entrypoints: `run_move_maker_agent` | Schemas: EnrichedCohort, OutcomeCharter, StrikePlan
- Service dependencies: get_services, registry | Helper utilities: build_move_maker_graph, generate_strike_plan
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Neurofoundry Agent

- Path: `backend/agents/neurofoundry_agent.py` | Entrypoints: none | Schemas: ADAPT20, AssetDNA, BehaviorPlan, CompileRequest, CompileResponse, EarnedEffort, EmailDraft, FramePlan, LandingOutline, MemeticRails, Pratfall, Rubric, SocialDraft, StyleMatch
- Service dependencies: no shared services | Helper utilities: build_dna, compile_asset, earned_effort_step, map_behavior, memetic_engine, normalize_adapt, pratfall_switch, select_frame, style_match
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Newsletter Agent

- Path: `backend/agents/newsletter_agent.py` | Entrypoints: `run_newsletter` | Schemas: NewsletterRequest, NewsletterResponse, NewsletterSection
- Service dependencies: get_services, registry | Helper utilities: build_newsletter_graph, draft_newsletter
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Objection Agent

- Path: `backend/agents/objection_agent.py` | Entrypoints: `run_objection_agent` | Schemas: Objection, PositioningOptionCard
- Service dependencies: get_services, registry | Helper utilities: build_objection_agent_graph, classify_objection, handle_error, patch_minor_objection, reframe_critical_objection, route_by_severity
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Objective Router Agent

- Path: `backend/agents/objective_router_agent.py` | Entrypoints: `run_objective_router` | Schemas: ADAPTPlan, AlignOut, ArchitectOut, DiagnoseOut, ObjectiveRouterRequest, ObjectiveRouterResponse, PilotOut, RouterClassifications, TrackOut, TrackTargets, WOOP
- Service dependencies: get_services, registry | Helper utilities: barbell_portfolio, canonicalize_objective, classify_orientation, default_metrics, diagnose_comb, pick_fogg_prompt, pick_game, select_north_star, targets_and_forecasts, woopize
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Outcome Agent

- Path: `backend/agents/outcome_agent.py` | Entrypoints: `run_outcome_committer_agent` | Schemas: EnrichedCohort, OutcomeCharter
- Service dependencies: get_services, registry | Helper utilities: build_outcome_committer_graph, draft_outcome_charter
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Partner Outreach Agent

- Path: `backend/agents/partner_outreach_agent.py` | Entrypoints: `run_partner_outreach` | Schemas: EnrichedPartner, OutreachTemplate, PartnerCandidate, PartnerOutreachCard, PartnerOutreachRequest, PartnerOutreachResponse
- Service dependencies: get_services, registry | Helper utilities: build_partner_outreach_graph, draft_outreach, enrich_partners, find_partners
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Permission Ladder Agent

- Path: `backend/agents/permission_ladder_agent.py` | Entrypoints: none | Schemas: CommunityEntry, GrowthLoop, MicroAsk, OptInStep, PermissionLadderBlueprint, PermissionLadderRequest, PermissionLadderResponse, PromptSpec, ReciprocityOffer
- Service dependencies: no shared services | Helper utilities: build_permission_ladder
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Persona Angle Agent

- Path: `backend/agents/persona_angle_agent.py` | Entrypoints: `run_persona_angle` | Schemas: PersonaAngleItem, PersonaAngleRequest, PersonaAngleResponse
- Service dependencies: get_services, registry | Helper utilities: build_persona_angle_graph, draft_angles
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Platform Ops Copilot Agent

- Path: `backend/agents/platform_ops_copilot_agent.py` | Entrypoints: `run_platform_vibe_check` | Schemas: ChecklistItem, SourceRef, VibeCheckRequest, VibeCheckResponse
- Service dependencies: get_services, registry | Helper utilities: internal nodes
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Poll Agent

- Path: `backend/agents/poll_agent.py` | Entrypoints: `run_poll` | Schemas: PollItem, PollRequest, PollResponse
- Service dependencies: get_services, registry | Helper utilities: build_poll_graph, draft_polls
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Positioning Agent

- Path: `backend/agents/positioning_agent.py` | Entrypoints: `run_positioning_agent` | Schemas: PositioningOptionCard
- Service dependencies: get_services, registry | Helper utilities: build_positioning_agent_graph, generate_positioning_options, sort_and_finalize, validate_and_score_options
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Press Release Agent

- Path: `backend/agents/press_release_agent.py` | Entrypoints: `run_press_release` | Schemas: PressReleaseRequest, PressReleaseResponse
- Service dependencies: get_services, registry | Helper utilities: build_press_graph, draft_press_release
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Push Agent

- Path: `backend/agents/push_agent.py` | Entrypoints: `run_push` | Schemas: PushRequest, PushResponse
- Service dependencies: get_services, registry | Helper utilities: build_push_graph, draft_push
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Restaurant Micro Strategy Agent

- Path: `backend/agents/restaurant_micro_strategy_agent.py` | Entrypoints: `run_restaurant_micro_strategy` | Schemas: ICEScore, MicroPlay, MicroPlayRequest, MicroPlayResponse, SourceRef
- Service dependencies: get_services, make_simple_pdf_base64, pdf_writer_service, registry | Helper utilities: internal nodes
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Rok Knife Agent

- Path: `backend/agents/rok_knife_agent.py` | Entrypoints: none | Schemas: BiasLock, ROKInput, ROKOutput, Spine, StoryPrimitives, Taglines, WeirdDir
- Service dependencies: no shared services | Helper utilities: generate_big_idea
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Scheduler Agent

- Path: `backend/agents/scheduler_agent.py` | Entrypoints: `run_scheduler_agent` | Schemas: AssetPackage, CreativeAsset, SchedulePackage, ScheduledJob, StrikePlan
- Service dependencies: no shared services | Helper utilities: build_schedule_package, build_scheduler_graph
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Seo Brief Agent

- Path: `backend/agents/seo_brief_agent.py` | Entrypoints: `run_seo_brief` | Schemas: OutlineSection, SEOBrief, SEOBriefRequest, SEOBriefResponse, SEOSourceNote
- Service dependencies: get_services, registry | Helper utilities: build_seo_brief_graph, collect_sources, note_sources, synthesize_brief
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Short Video Agent

- Path: `backend/agents/short_video_agent.py` | Entrypoints: `run_short_video` | Schemas: ShortVideoRequest, ShortVideoResponse, VideoBeat
- Service dependencies: get_services, registry | Helper utilities: build_short_video_graph, draft_video
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Sms Agent

- Path: `backend/agents/sms_agent.py` | Entrypoints: `run_sms` | Schemas: SMSRequest, SMSResponse
- Service dependencies: get_services, registry | Helper utilities: build_sms_graph, draft_sms
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Social Calendar Agent

- Path: `backend/agents/social_calendar_agent.py` | Entrypoints: `run_social_calendar` | Schemas: SocialCalendarRequest, SocialCalendarResponse, SocialPostPlan
- Service dependencies: get_services, registry | Helper utilities: build_social_calendar_graph, draft_ideas, gather_signals, plan_themes, schedule_posts
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Strategy Engine

- Path: `backend/agents/strategy_engine.py` | Entrypoints: `run_action`, `run_aisas`, `run_cash`, `run_cashguard`, `run_lateral_vertical`, `run_offer`, `run_permission`, `run_reframe`, `run_segment`, `run_wound` | Schemas: AISASRequest, AISASResponse, ActionOut, ActionRequest, CashGuardRequest, CashGuardResponse, CashOut, CashRequest, LateralVerticalRequest, LateralVerticalResponse, OfferOut, OfferRequest, OutreachMsg, PermissionRequest, PermissionResponse, Play, ReframeOut, ReframeRequest, SegmentOut, SegmentRequest, WoundOut, WoundRequest
- Service dependencies: get_services, registry | Helper utilities: internal nodes
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Synthetic Behavior Agent

- Path: `backend/agents/synthetic_behavior_agent.py` | Entrypoints: `run_synthetic_generation` | Schemas: CohortDataset, CohortSpec, SourceRef, SyntheticGenRequest, SyntheticGenResponse, SyntheticPerson
- Service dependencies: get_services, registry | Helper utilities: build_rules, build_synthetic_graph, pattern_mining_for, sample_people, sdv_augment, survey_synthesis, validate_dataset
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Synthetic Pipeline Agent

- Path: `backend/agents/synthetic_pipeline_agent.py` | Entrypoints: `run_synthetic_icp_pipeline` | Schemas: GeoSignal, MarketNeedReport, SyntheticGenRequest
- Service dependencies: no shared services | Helper utilities: internal nodes
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Tagline Agent

- Path: `backend/agents/tagline_agent.py` | Entrypoints: `run_tagline` | Schemas: TaglineRequest, TaglineResponse
- Service dependencies: get_services, registry | Helper utilities: build_tagline_graph, draft_taglines
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Testimonial Agent

- Path: `backend/agents/testimonial_agent.py` | Entrypoints: `run_testimonial` | Schemas: TestimonialRequest, TestimonialResponse
- Service dependencies: get_services, registry | Helper utilities: build_testimonial_graph, draft_testimonials
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Thread Agent

- Path: `backend/agents/thread_agent.py` | Entrypoints: `run_thread` | Schemas: ThreadRequest, ThreadResponse
- Service dependencies: get_services, registry | Helper utilities: build_thread_graph, draft_thread
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

### Agent: Whatsapp Agent

- Path: `backend/agents/whatsapp_agent.py` | Entrypoints: `run_whatsapp` | Schemas: WhatsAppRequest, WhatsAppResponse
- Service dependencies: get_services, registry | Helper utilities: build_whatsapp_graph, draft_whatsapp
- Notes: LangGraph workflow with structured outputs and `{"error": ...}` safety contract.

## Multi-Agent Workflows

`agent_hub.run_workflow` enables multi-step compositions. Define tasks with dependencies to 
chain agents without writing additional orchestration code.

- Workflow schema: see `schemas.a2a_schemas.WorkflowRequest` for the JSON contract consumed by the hub.
- Dependency resolution: tasks execute only after their `depends_on` tasks reach a completed or skipped state.
- Context templating: reference prior outputs using `{{tasks.<task_id>.<field>}}` placeholders in the downstream input payloads.
- Failure modes: choose `on_error='stop'` to halt the entire workflow or allow downstream steps to continue.
- Audit trail: responses include `events` with timestamps and task-level status messages for debugging.

## Service Registry

Services provide reusable integrations and shared infrastructure. They are initialized during 
FastAPI startup and injected into agents through `services.registry`.

### Service: Calendar Service

- Path: `backend/services/calendar_service.py` | Classes: utility functions
- Public helpers: `build_ics_event` | Consuming agents: chat_orchestrator
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Calendar Sync Service

- Path: `backend/services/calendar_sync_service.py` | Classes: `CalendarSyncService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Canva Service

- Path: `backend/services/canva_service.py` | Classes: `CanvaService`
- Public helpers: methods on service class | Consuming agents: canva_agent
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Connector Manager

- Path: `backend/services/connector_manager.py` | Classes: `ConnectorInfo`, `ConnectorManager`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Crawl Service

- Path: `backend/services/crawl_service.py` | Classes: `CrawlService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Discord Service

- Path: `backend/services/discord_service.py` | Classes: `DiscordService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Embedding Service

- Path: `backend/services/embedding_service.py` | Classes: `EmbeddingService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Facebook Service

- Path: `backend/services/facebook_service.py` | Classes: `FacebookItem`, `FacebookService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Ga4 Service

- Path: `backend/services/ga4_service.py` | Classes: `GA4Service`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Gmail Service

- Path: `backend/services/gmail_service.py` | Classes: `GmailService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Google Calendar Service

- Path: `backend/services/google_calendar_service.py` | Classes: `GoogleCalendarService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Google Docs Service

- Path: `backend/services/google_docs_service.py` | Classes: `GoogleDocsService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Google Forms Service

- Path: `backend/services/google_forms_service.py` | Classes: `GoogleFormsService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Google Maps Service

- Path: `backend/services/google_maps_service.py` | Classes: `POI`, `GoogleMapsService`
- Public helpers: methods on service class | Consuming agents: market_analysis_agent
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Google Sheets Service

- Path: `backend/services/google_sheets_service.py` | Classes: `GoogleSheetsService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Hackernews Service

- Path: `backend/services/hackernews_service.py` | Classes: `HNItem`, `HackerNewsService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Instagram Service

- Path: `backend/services/instagram_service.py` | Classes: `InstagramItem`, `InstagramService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Instrumentation Service

- Path: `backend/services/instrumentation_service.py` | Classes: `ConnectorStats`, `InstrumentationService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Keywords Service

- Path: `backend/services/keywords_service.py` | Classes: `KeywordService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Link Preview Service

- Path: `backend/services/link_preview_service.py` | Classes: `LinkPreview`, `LinkPreviewService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Linkedin Service

- Path: `backend/services/linkedin_service.py` | Classes: `LinkedInItem`, `LinkedInService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Mastodon Service

- Path: `backend/services/mastodon_service.py` | Classes: `MastodonItem`, `MastodonService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Medium Service

- Path: `backend/services/medium_service.py` | Classes: `MediumItem`, `MediumService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Moderation Service

- Path: `backend/services/moderation_service.py` | Classes: `ModerationReport`, `ModerationService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Ner Service

- Path: `backend/services/ner_service.py` | Classes: `Entities`, `NERService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: News Service

- Path: `backend/services/news_service.py` | Classes: `NewsItem`, `NewsService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Notion Service

- Path: `backend/services/notion_service.py` | Classes: `NotionService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Oauth Service

- Path: `backend/services/oauth_service.py` | Classes: `ProviderConfig`, `OAuthService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Pdf Service

- Path: `backend/services/pdf_service.py` | Classes: `PDFService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Pdf Writer Service

- Path: `backend/services/pdf_writer_service.py` | Classes: utility functions
- Public helpers: `make_simple_pdf_base64` | Consuming agents: chat_orchestrator, restaurant_micro_strategy_agent
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Pinterest Service

- Path: `backend/services/pinterest_service.py` | Classes: `PinterestItem`, `PinterestService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Producthunt Service

- Path: `backend/services/producthunt_service.py` | Classes: `ProductHuntItem`, `ProductHuntService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Quora Service

- Path: `backend/services/quora_service.py` | Classes: `QuoraItem`, `QuoraService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Reddit Service

- Path: `backend/services/reddit_service.py` | Classes: `RedditPost`, `RedditService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Registry

- Path: `backend/services/registry.py` | Classes: `Services`
- Public helpers: `init_services`, `get_services`, `shutdown_services` | Consuming agents: ad_copy_agent, archive_agent, asset_supervisor_agent, blog_outline_agent, canva_agent, caption_agent, carousel_agent, case_study_outline_agent, chat_orchestrator, cohort_agent, competitor_intel_agent, creative_agent, cta_agent, deep_research_agent, drip_campaign_agent, dynamic_intake_agent, email_agent, evidence_linker_agent, giveaway_agent, google_forms_agent, hashtag_agent, headline_agent, hook_agent, icp_builder_agent, image_prompt_agent, intake_agent, landing_page_agent, market_analysis_agent, meme_agent, move_maker_agent, newsletter_agent, objection_agent, objective_router_agent, outcome_agent, partner_outreach_agent, persona_angle_agent, platform_ops_copilot_agent, poll_agent, positioning_agent, press_release_agent, push_agent, restaurant_micro_strategy_agent, seo_brief_agent, short_video_agent, sms_agent, social_calendar_agent, strategy_engine, synthetic_behavior_agent, tagline_agent, testimonial_agent, thread_agent, whatsapp_agent
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Rss Service

- Path: `backend/services/rss_service.py` | Classes: `FeedItem`, `RSSService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Search Service

- Path: `backend/services/search_service.py` | Classes: `SearchResult`, `SearchService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Social Service

- Path: `backend/services/social_service.py` | Classes: `SocialResults`, `SocialService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Stackoverflow Service

- Path: `backend/services/stackoverflow_service.py` | Classes: `StackOverflowItem`, `StackOverflowService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Substack Service

- Path: `backend/services/substack_service.py` | Classes: `SubstackItem`, `SubstackService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Summarization Service

- Path: `backend/services/summarization_service.py` | Classes: `SummarizationService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Threads Service

- Path: `backend/services/threads_service.py` | Classes: `ThreadsItem`, `ThreadsService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Tiktok Service

- Path: `backend/services/tiktok_service.py` | Classes: `TikTokItem`, `TikTokService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Tone Service

- Path: `backend/services/tone_service.py` | Classes: `ToneService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Topic Cluster Service

- Path: `backend/services/topic_cluster_service.py` | Classes: `TopicClusterService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Translation Service

- Path: `backend/services/translation_service.py` | Classes: `TranslationService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Twitter X Service

- Path: `backend/services/twitter_x_service.py` | Classes: `Tweet`, `TwitterXService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: User Store Service

- Path: `backend/services/user_store_service.py` | Classes: `User`, `UserStoreService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Web Scraper Service

- Path: `backend/services/web_scraper_service.py` | Classes: `WebScraperService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Wikipedia Service

- Path: `backend/services/wikipedia_service.py` | Classes: `WikipediaService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Youtube Data Service

- Path: `backend/services/youtube_data_service.py` | Classes: `YouTubeDataService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Youtube Search Service

- Path: `backend/services/youtube_search_service.py` | Classes: `VideoItem`, `YouTubeSearchService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

### Service: Youtube Service

- Path: `backend/services/youtube_service.py` | Classes: `YouTubeService`
- Public helpers: methods on service class | Consuming agents: not referenced by agents
- Notes: review credentials in `core.config.Settings` and mock external calls during tests.

## Schema Library

Pydantic schemas guarantee consistent contracts across HTTP handlers and agents. Reference this 
catalog when extending request bodies or designing UI forms.

### Schema Module: A2A Schemas

- Path: `backend/schemas/a2a_schemas.py` | Models: TaskSpec, WorkflowRequest, TaskEvent, WorkflowResult | Enums: none
- Agents using these models: agent_hub
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Archive Schemas

- Path: `backend/schemas/archive_schemas.py` | Models: PlaybookTemplate, NextMoveRecommendation | Enums: none
- Agents using these models: archive_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Asset Schemas

- Path: `backend/schemas/asset_schemas.py` | Models: MemeRequest, MemeResponse, CarouselRequest, CarouselSlide, CarouselResponse, ShortVideoRequest, VideoBeat, ShortVideoResponse, SupervisorRequest, SupervisorResponse, AdCopyRequest, AdVariant, AdCopyResponse, ImagePromptRequest, ImagePromptResponse, ThreadRequest, ThreadResponse, HeadlineRequest, HeadlineResponse, TaglineRequest, TaglineResponse, HashtagRequest, HashtagResponse, EmailRequest, EmailResponse, SMSRequest, SMSResponse, PushRequest, PushResponse, BlogOutlineRequest, BlogSection, BlogOutlineResponse, PressReleaseRequest, PressReleaseResponse, WhatsAppRequest, WhatsAppResponse, PollItem, PollRequest, PollResponse, GiveawayRequest, GiveawayResponse, TestimonialRequest, TestimonialResponse, DripEmail, DripCampaignRequest, DripCampaignResponse, CtaRequest, CtaResponse, HookRequest, HookResponse, CaptionRequest, CaptionResponse, NewsletterSection, NewsletterRequest, NewsletterResponse, PersonaAngleItem, PersonaAngleRequest, PersonaAngleResponse, CaseStudySection, CaseStudyOutlineRequest, CaseStudyOutlineResponse | Enums: none
- Agents using these models: ad_copy_agent, asset_supervisor_agent, blog_outline_agent, caption_agent, carousel_agent, case_study_outline_agent, cta_agent, drip_campaign_agent, email_agent, giveaway_agent, hashtag_agent, headline_agent, hook_agent, image_prompt_agent, meme_agent, newsletter_agent, persona_angle_agent, poll_agent, press_release_agent, push_agent, short_video_agent, sms_agent, tagline_agent, testimonial_agent, thread_agent, whatsapp_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Attribution Schemas

- Path: `backend/schemas/attribution_schemas.py` | Models: AttributionEvent, ProofArtifact, AttributionReport | Enums: none
- Agents using these models: archive_agent, attribution_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Canva Schemas

- Path: `backend/schemas/canva_schemas.py` | Models: CanvaDesignRequest, CanvaDesignResponse | Enums: none
- Agents using these models: canva_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Chat Schemas

- Path: `backend/schemas/chat_schemas.py` | Models: Attachment, ActionLog, ChatTurnRequest, ChatTurnResponse | Enums: none
- Agents using these models: chat_orchestrator
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Cohort Schemas

- Path: `backend/schemas/cohort_schemas.py` | Models: CohortStrategy, EnrichedCohort, CohortStrategyReport | Enums: none
- Agents using these models: cohort_agent, move_maker_agent, outcome_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Competitor Schemas

- Path: `backend/schemas/competitor_schemas.py` | Models: CompetitorScanRequest, CompetitorSignal, CompetitorCard, CompetitorScanResponse | Enums: none
- Agents using these models: agent_hub, competitor_intel_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Creative Schemas

- Path: `backend/schemas/creative_schemas.py` | Models: CreativeAsset, AssetPackage | Enums: none
- Agents using these models: creative_agent, launch_agent, scheduler_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Dynamic Intake Schemas

- Path: `backend/schemas/dynamic_intake_schemas.py` | Models: IntakeHints, PersonaProfile, DynamicStartRequest, DynamicStartResponse, DynamicTurnRequest, DynamicTurnResponse | Enums: none
- Agents using these models: dynamic_intake_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Evidence Schemas

- Path: `backend/schemas/evidence_schemas.py` | Models: CopyAuditRequest, EvidenceItem, ClaimItem, ClaimEvidence, CopyAuditResponse, RewriteOption, ApplyChange, RewriteApplyRequest, RewriteApplyResponse | Enums: none
- Agents using these models: evidence_linker_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Founder Brand Schemas

- Path: `backend/schemas/founder_brand_schemas.py` | Models: CompetitorSnapshot, BrandVoice, MeasurementTier, FounderBrandInput, FounderBrandCodex, FounderBrandResponse | Enums: none
- Agents using these models: founder_brand_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Geo Schemas

- Path: `backend/schemas/geo_schemas.py` | Models: LocationRequest, GeoSignal, MarketNeedReport | Enums: none
- Agents using these models: agent_hub, icp_builder_agent, market_analysis_agent, synthetic_pipeline_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Icp Schemas

- Path: `backend/schemas/icp_schemas.py` | Models: ICPCard, Cohort, ICPReport | Enums: none
- Agents using these models: cohort_agent, icp_builder_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Intake Schemas

- Path: `backend/schemas/intake_schemas.py` | Models: IntakeState | Enums: none
- Agents using these models: intake_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Landing Schemas

- Path: `backend/schemas/landing_schemas.py` | Models: LandingPageRequest, HeroSection, PageSection, FAQItem, LandingPageBlueprint, LandingPageResponse | Enums: none
- Agents using these models: landing_page_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Launch Schemas

- Path: `backend/schemas/launch_schemas.py` | Models: Contact, OutboundMessage, CampaignLogEntry, LaunchReport | Enums: none
- Agents using these models: launch_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Move Schemas

- Path: `backend/schemas/move_schemas.py` | Models: Experiment, AssetBrief, ScheduledAction, StrikePlan | Enums: none
- Agents using these models: archive_agent, creative_agent, move_maker_agent, scheduler_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Neurofoundry Schemas

- Path: `backend/schemas/neurofoundry_schemas.py` | Models: ADAPTAudience, ADAPTOutcome, ProofAsset, ADAPTTiming, ADAPT20, FramePlan, BehaviorBMAP, BehaviorCOMB, BehaviorEAST, BehaviorPlan, AssetDNA, MemeticRails, StyleMatch, EarnedEffort, Pratfall, CompileRequest, EmailDraft, SocialDraft, LandingOutline, Rubric, CompileResponse | Enums: none
- Agents using these models: neurofoundry_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Normalized

- Path: `backend/schemas/normalized.py` | Models: Asset, Post, Comment, Event, Metric | Enums: none
- Agents using these models: google_forms_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Oauth Schemas

- Path: `backend/schemas/oauth_schemas.py` | Models: OAuthProviderInfo, OAuthToken | Enums: none
- Agents using these models: not referenced
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Objection Schemas

- Path: `backend/schemas/objection_schemas.py` | Models: Objection, ObjectionHandlingRequest, ObjectionHandlingResponse | Enums: none
- Agents using these models: objection_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Objective Router Schemas

- Path: `backend/schemas/objective_router_schemas.py` | Models: ICPProfile, ObjectiveRouterRequest, WOOP, AlignOut, DiagnoseOut, ArchitectOut, PilotOut, TrackTargets, TrackOut, ADAPTPlan, RouterClassifications, ObjectiveRouterResponse | Enums: none
- Agents using these models: objective_router_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Ops Schemas

- Path: `backend/schemas/ops_schemas.py` | Models: SourceRef, ICEScore, MicroPlay, MicroPlayRequest, MicroPlayResponse, ChecklistItem, VibeCheckRequest, VibeCheckResponse | Enums: none
- Agents using these models: platform_ops_copilot_agent, restaurant_micro_strategy_agent, synthetic_behavior_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Outcome Schemas

- Path: `backend/schemas/outcome_schemas.py` | Models: OutcomeCharter | Enums: none
- Agents using these models: archive_agent, creative_agent, move_maker_agent, outcome_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Partner Schemas

- Path: `backend/schemas/partner_schemas.py` | Models: PartnerOutreachRequest, PartnerCandidate, EnrichedPartner, OutreachTemplate, PartnerOutreachCard, PartnerOutreachResponse | Enums: none
- Agents using these models: partner_outreach_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Permission Ladder Schemas

- Path: `backend/schemas/permission_ladder_schemas.py` | Models: ReciprocityOffer, MicroAsk, PromptSpec, OptInStep, CommunityEntry, GrowthLoop, PermissionLadderBlueprint, PermissionLadderRequest, PermissionLadderResponse | Enums: none
- Agents using these models: dynamic_intake_agent, permission_ladder_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Positioning Schemas

- Path: `backend/schemas/positioning_schemas.py` | Models: PositioningOptionCard, PositioningGenerationRequest, PositioningResponse | Enums: none
- Agents using these models: agent_hub, objection_agent, positioning_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Research Schemas

- Path: `backend/schemas/research_schemas.py` | Models: ResearchRequest, SourceNote, ResearchFinding, ResearchResponse | Enums: none
- Agents using these models: deep_research_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Rok Schemas

- Path: `backend/schemas/rok_schemas.py` | Models: ROKInput, Spine, BiasLock, StoryPrimitives, WeirdDir, Taglines, ROKOutput | Enums: none
- Agents using these models: rok_knife_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Scheduler Schemas

- Path: `backend/schemas/scheduler_schemas.py` | Models: ScheduledJob, SchedulePackage | Enums: none
- Agents using these models: launch_agent, scheduler_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Seo Schemas

- Path: `backend/schemas/seo_schemas.py` | Models: SEOSourceNote, SEOBriefRequest, OutlineSection, SEOBrief, SEOBriefResponse | Enums: none
- Agents using these models: seo_brief_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Social Calendar Schemas

- Path: `backend/schemas/social_calendar_schemas.py` | Models: SocialCalendarRequest, SocialPostPlan, SocialCalendarResponse | Enums: none
- Agents using these models: social_calendar_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Strategy Schemas

- Path: `backend/schemas/strategy_schemas.py` | Models: Tribe, SegmentOut, WoundOut, ReframeOut, OfferOut, OutreachMsg, ActionOut, CashOut, GovernanceOut, Play, SegmentRequest, WoundRequest, ReframeRequest, OfferRequest, ActionRequest, CashRequest, CashGuardRequest, CashGuardResponse, PermissionRequest, PermissionResponse, LateralVerticalRequest, LateralVerticalResponse, AISASRequest, AISASResponse | Enums: none
- Agents using these models: agent_hub, strategy_engine
- Notes: extend models with field constraints and type hints to improve generated docs.

### Schema Module: Synthetic Schemas

- Path: `backend/schemas/synthetic_schemas.py` | Models: Demographic, Economic, Psychographic, SocialCultural, Behavioral, Trust, SourceRef, CohortSpec, SyntheticPerson, CohortDataset, SyntheticGenRequest, SyntheticGenResponse | Enums: none
- Agents using these models: platform_ops_copilot_agent, restaurant_micro_strategy_agent, synthetic_behavior_agent, synthetic_pipeline_agent
- Notes: extend models with field constraints and type hints to improve generated docs.

## API Surface

FastAPI routers expose every capability via versioned `/api/v1/*` endpoints. Endpoints respond 
with JSON and leverage Pydantic models for automatic documentation in Swagger UI.

### Router: A2A

- File: `backend/api/v1/a2a.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Archive

- File: `backend/api/v1/archive.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Assets

- File: `backend/api/v1/assets.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Auth

- File: `backend/api/v1/auth.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Chat

- File: `backend/api/v1/chat.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Cohorts

- File: `backend/api/v1/cohorts.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Competitors

- File: `backend/api/v1/competitors.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Config

- File: `backend/api/v1/config.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Creatives

- File: `backend/api/v1/creatives.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Evidence

- File: `backend/api/v1/evidence.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Founder Brand

- File: `backend/api/v1/founder_brand.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Geo Analysis

- File: `backend/api/v1/geo_analysis.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Google Sheets

- File: `backend/api/v1/google_sheets.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Icp

- File: `backend/api/v1/icp.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Intake Interview

- File: `backend/api/v1/intake_interview.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Intake Orchestration

- File: `backend/api/v1/intake_orchestration.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Integrations

- File: `backend/api/v1/integrations.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Landing

- File: `backend/api/v1/landing.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Launch

- File: `backend/api/v1/launch.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Moves

- File: `backend/api/v1/moves.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Neurofoundry

- File: `backend/api/v1/neurofoundry.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Oauth

- File: `backend/api/v1/oauth.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Objection

- File: `backend/api/v1/objection.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Objective Router

- File: `backend/api/v1/objective_router.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Ops

- File: `backend/api/v1/ops.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Outcomes

- File: `backend/api/v1/outcomes.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Partners

- File: `backend/api/v1/partners.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Permission Ladder

- File: `backend/api/v1/permission_ladder.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Positioning

- File: `backend/api/v1/positioning.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Research

- File: `backend/api/v1/research.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Rok

- File: `backend/api/v1/rok.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Scheduler

- File: `backend/api/v1/scheduler.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Seo

- File: `backend/api/v1/seo.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Social Calendar

- File: `backend/api/v1/social_calendar.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Strategy

- File: `backend/api/v1/strategy.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Synthetic

- File: `backend/api/v1/synthetic.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

### Router: Synthetic Pipeline

- File: `backend/api/v1/synthetic_pipeline.py`
- Routes: Router defines dependencies but no explicit HTTP handlers.
- Test guidance: use FastAPI TestClient with sample payloads to validate response objects.

## Frontend and UX

- React shell: `web/src/App.tsx` renders a placeholder view; extend it with routing, query clients, and authentication flows.
- Dev proxy: `vite.config.ts` proxies `/api` calls to FastAPI, simplifying local development without CORS headaches.
- Static concept: `frontend/index.html` demonstrates the intended multi-pane strategist cockpit using Tailwind CSS.
- Build artifact: `npm run build` emits assets to `web/dist/` for static hosting experiments.
- Environment exposure: prefix frontend env variables with `VITE_` to make them available during bundling.

## Developer Tooling

- Use `uvicorn` reloads by setting `UVICORN_RELOAD=1` for iterative backend development.
- `backend/agents/utils/toolkit.py` and `postprocess.py` host reusable prompt helpers and text normalization routines.
- `backend/services/utils/retry_cache.py` implements memoization for expensive API calls and rate-limited endpoints.
- `dev.ps1` automates virtual environment creation and dependency installation on Windows.
- Consider adding VS Code tasks or Make targets if you frequently run combined backend and frontend workflows.

## Observability

Logging and diagnostics keep local deployments transparent.

- Startup logs: look for Ollama model availability and ChromaDB connection counts in the FastAPI console.
- Agent markers: every agent emits a start log and structured warnings for validation issues.
- HTTP validation: FastAPI's 422 handler returns field-level errors with counts and paths.
- Service warnings: optional integrations (Google, Canva, Discord) log when credentials are missing rather than crashing startup.
- Telemetry hooks: extend `services.instrumentation_service.InstrumentationService` to capture custom metrics.

## Security

- Keep `.env` files outside version control; they may contain OAuth secrets and API keys.
- Limit network exposure: default ports (8000, 5173, 8001) are bound to localhost.
- Review OAuth scopes in `services/oauth_service.py` before granting production permissions.
- Disable automatic browser launches by setting `AUTO_OPEN_BROWSER=0` when running on shared machines.
- Audit third-party SDKs for storage behavior; most services avoid persisting tokens by default.

## Extension Recipes

Extend Geo-Strategist by following these structured workflows.

### New Agent Checklist

- Clone an existing agent module as a template; retain LangGraph structure for predictability.
- Define request/response models in the relevant schema file, annotating optional fields and defaults.
- Fetch shared services via `get_services()` and gate usage behind availability checks to support offline runs.
- Return dictionaries using `model_dump()` to maintain JSON serializability for FastAPI responses.
- Update `agent_hub.AGENT_REGISTRY` and add routing in `api/v1` if the agent is exposed via HTTP.

### New Service Checklist

- Create `<name>_service.py` with a class encapsulating external API logic and optional credential detection.
- Add initialization to `services.registry.init_services` and track the instance in the `Services` dataclass.
- Document required environment variables in `.env.example` and in this manual.
- Write defensive wrappers for network calls using timeouts and error translation for agents.
- Add integration tests or manual verification scripts before depending on the new service in production workflows.

### Schema Evolution Strategy

- Prefer additive changes to maintain backward compatibility with existing clients.
- Capture breaking changes in release notes and coordinate frontend updates in tandem.
- Use Pydantic validators for derived fields or conditional requirements (e.g., `@model_validator`).
- Provide example payloads in this README to accelerate QA and documentation.

## Testing Strategy

- Target high-value agents with unit tests that stub LangChain calls and assert deterministic outputs.
- Leverage FastAPI TestClient to hit HTTP endpoints using schema-generated sample data.
- Use pytest markers to separate fast unit tests from integration tests that exercise real services.
- Mock OAuth flows by injecting fake tokens into service constructors during tests.
- Consider contract tests that validate workflow orchestration via `agent_hub.run_workflow` with small DAGs.

## Deployment Playbooks

- Containerize backend and Ollama together when deploying to a headless server; mount `chroma_db/` as a volume.
- Use process managers (systemd, NSSM) to keep FastAPI and Ollama daemons alive on restart.
- Front deployments with a reverse proxy that handles TLS, compression, and caching of static assets.
- Schedule periodic cleanups of `chroma_db/` if embeddings are regenerated frequently.
- Monitor third-party API quotas and configure alerting when approaching provider limits.

## Troubleshooting

- 422 errors: inspect validation responses for missing required fields or invalid enum values.
- Ollama unavailable: ensure the daemon is running and the configured models are pulled (`ollama pull <model>`).
- Vector store missing: start ChromaDB or set `CHROMA_PORT` to a reachable instance; agents fallback to baseline prompts when absent.
- OAuth failures: verify redirect URIs and ensure credentials are present in `.env`.
- CORS issues: confirm requests pass through the Vite proxy or update allowed origins in `main.py`.

## Glossary

- Agent: LangGraph workflow that produces a marketing artifact or decision.
- Service: Shared integration or utility accessible via `services.registry`.
- Schema: Pydantic model describing request/response structure for agents and APIs.
- Workflow: Orchestrated execution of multiple agents with dependency awareness.
- Playbook Template: Stored knowledge in ChromaDB powering reusable strategies and prompts.

## Operational Checklists

Use these reminders during daily operations and before releases.

- Before running: confirm Ollama, ChromaDB, and FastAPI ports are free.
- Before demos: preload critical prompts and fetch OAuth tokens for Google/Canva accounts.
- Before commits: run linting and manual smoke tests for modified endpoints.
- Before releases: update this manual, `.env.example`, and maintainers on new capabilities.
- After failures: capture logs, input payloads, and reproduction steps for debugging.

## Appendix A. Environment Variables

Consolidated reference of environment variables discovered in example files.

- `CANVA_BRAND_COLORS` (default `#6420FF,#111111,#FFFFFF`)
- `CANVA_CLIENT_ID` (default ``)
- `CANVA_CLIENT_ID` (default `your_canva_client_id`)
- `CANVA_CLIENT_SECRET` (default ``)
- `CANVA_CLIENT_SECRET` (default `your_canva_client_secret`)
- `CANVA_SCOPES` (default ``)
- `CANVA_TEMPLATE_URL` (default ``)
- `CHROMA_HOST` (default `localhost`)
- `CHROMA_PORT` (default `8001`)
- `DISCORD_BOT_TOKEN` (default ``)
- `DISCORD_CLIENT_ID` (default ``)
- `DISCORD_CLIENT_SECRET` (default ``)
- `EXPOSE_SERVER_MAPS_KEY_TO_FRONTEND` (default `0`)
- `GOOGLE_CLIENT_ID` (default ``)
- `GOOGLE_CLIENT_ID` (default `your_google_client_id`)
- `GOOGLE_CLIENT_SECRET` (default ``)
- `GOOGLE_CLIENT_SECRET` (default `your_google_client_secret`)
- `GOOGLE_MAPS_API_KEY` (default `your_maps_key`)
- `GOOGLE_MAPS_BROWSER_API_KEY` (default `your_browser_key`)
- `NOTION_CLIENT_ID` (default ``)
- `NOTION_CLIENT_SECRET` (default ``)
- `NOTION_OAUTH_AUTH_URL` (default `https://api.notion.com/v1/oauth/authorize`)
- `NOTION_OAUTH_TOKEN_URL` (default `https://api.notion.com/v1/oauth/token`)
- `OAUTH_CANVA_AUTH_URL` (default ``)
- `OAUTH_CANVA_AUTH_URL` (default `https://example.canva.auth/authorize`)
- `OAUTH_CANVA_TOKEN_URL` (default ``)
- `OAUTH_CANVA_TOKEN_URL` (default `https://example.canva.auth/token`)
- `OLLAMA_EMBEDDINGS_MODEL` (default `jina-embeddings-v2-base-en`)
- `OLLAMA_EMBEDDINGS_MODEL` (default `nomic-embed-text`)
- `OLLAMA_FAST_MODEL` (default `gemma3:1b`)
- `OLLAMA_HOST` (default `localhost`)
- `OLLAMA_PORT` (default `11434`)
- `OLLAMA_REASONING_MODEL` (default `gemma3:4b`)
- `PUBLIC_BASE_URL` (default `http://localhost:8000`)
- `REDDIT_CLIENT_ID` (default ``)
- `REDDIT_CLIENT_SECRET` (default ``)
- `REDDIT_USER_AGENT` (default `geo-strategist/1.0`)
- `SENDGRID_API_KEY` (default ``)
- `SKIP_BOOTSTRAP` (default `0`)
- `SMTP_HOST` (default `smtp.example.com`)
- `SMTP_PASS` (default `app_password`)
- `SMTP_PORT` (default `587`)
- `SMTP_TLS` (default `1`)
- `SMTP_USER` (default `me@example.com`)
- `TRELLO_API_KEY` (default ``)
- `TRELLO_API_TOKEN` (default ``)
- `TWITTER_BEARER_TOKEN` (default ``)
- `UNSPLASH_ACCESS_KEY` (default ``)
- `X_BEARER_TOKEN` (default ``)
- `YOUTUBE_API_KEY` (default ``)

## Appendix B. Agent-Service Map

Agent | Services
--- | ---
ad_copy_agent | get_services, registry
agent_hub | None
archive_agent | get_services, registry
asset_supervisor_agent | get_services, registry
attribution_agent | None
blog_outline_agent | get_services, registry
canva_agent | CanvaService, canva_service, get_services, registry
caption_agent | get_services, registry
carousel_agent | get_services, registry
case_study_outline_agent | get_services, registry
chat_orchestrator | build_ics_event, calendar_service, get_services, make_simple_pdf_base64, pdf_writer_service, registry
- Supplemental note 1: Archive governance ensures stale entries rotate quarterly.
- Supplemental note 2: Validate OAuth redirect URIs after any domain change.
- Supplemental note 3: Keep agent prompt libraries versioned for reproducibility.
