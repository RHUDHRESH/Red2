import uuid
import logging
import json
from typing import TypedDict, List

import chromadb
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_community.vectorstores.chroma import Chroma
from langchain_ollama.embeddings import OllamaEmbeddings
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.outcome_schemas import OutcomeCharter
from schemas.move_schemas import StrikePlan
from schemas.attribution_schemas import AttributionReport
from schemas.archive_schemas import PlaybookTemplate, NextMoveRecommendation

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models & Lazy Services ---
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.2, base_url=settings.OLLAMA_BASE_URL)

# Lazily initialize Chroma + embeddings so the app can start without services
_vectorstore = None

def get_vectorstore():
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore
    try:
        # Try shared services first
        try:
            services = get_services()
            if services.vectorstore is not None:
                _vectorstore = services.vectorstore
                return _vectorstore
            embeddings = services.embeddings
        except Exception:
            embeddings = OllamaEmbeddings(model=settings.OLLAMA_EMBEDDINGS_MODEL)

        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
        _vectorstore = Chroma(
            client=client,
            collection_name="playbook_templates",
            embedding_function=embeddings,
        )
        logger.info(
            f"Connected to ChromaDB collection 'playbook_templates'. Count: {_vectorstore._collection.count()}"
        )
        return _vectorstore
    except Exception as e:
        logger.warning(f"ChromaDB not available at {settings.CHROMA_HOST}:{settings.CHROMA_PORT} - {e}")
        return None

# --- Agent States ---
class ArchiveAgentState(TypedDict):
    """State for the process of archiving a successful campaign."""
    strike_plan: StrikePlan
    outcome_charter: OutcomeCharter
    attribution_report: AttributionReport
    playbook_template: PlaybookTemplate | None
    error: str | None

class RecommendAgentState(TypedDict):
    """State for the process of recommending a next move."""
    new_goal: str
    retrieved_docs: List[Document]
    recommendation: NextMoveRecommendation | None
    error: str | None

# --- Pydantic Models for Structured LLM Outputs ---
class PlaybookGeneratorTool(BaseModel):
    """Tool for the LLM to generate the core content of a PlaybookTemplate."""
    move_type: str = Field(..., description="A high-level category for the playbook, e.g., 'New Customer Acquisition', 'Holiday Promotion'.")
    target_icp_labels: List[str] = Field(..., description="Keywords describing the target ICP, e.g., ['college_students', 'tech_park_employees'].")
    description: str = Field(..., description="A human-readable summary of what this playbook does, its strategy, and when it should be used.")

# --- ARCHIVING AGENT ---

def parameterize_and_summarize(state: ArchiveAgentState) -> ArchiveAgentState:
    """Uses an LLM to analyze a completed campaign and distill it into a reusable template."""
    logger.info("--- Node: Parameterizing and Summarizing Playbook ---")
    try:
        generator_tool = _get_reasoning_llm().with_structured_output(PlaybookGeneratorTool)
        charter = state['outcome_charter']
        plan = state['strike_plan']
        report = state['attribution_report']

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a strategic analyst. Your job is to analyze a completed marketing campaign and distill its essence into a reusable playbook template. "
             "Focus on the 'what' and 'why' of the strategy. Extract the core themes and target audience to create searchable metadata. "
             "Use the 'PlaybookGeneratorTool' to format your response."),
            ("human",
             "Please analyze the following successful campaign materials and generate a playbook summary.\n\n"
             "**Outcome Charter**:\nObjective: {objective}\nMetric: {metric}\nResult: Achieved {target} (vs. baseline of {baseline})\n\n"
             "**Strike Plan Summary**:\nThis plan used the following channels: {channels}. It ran for {duration} days and targeted the '{cohort_name}' cohort.\n\n"
             "**Performance Summary**:\nTotal Revenue: ₹{revenue:,.2f}\nTotal Orders: {orders}\n\n"
             "Based on all this, please generate the playbook summary.")
        ])
        
        chain = prompt | generator_tool
        result = chain.invoke({
            "objective": charter.objective,
            "metric": f"{charter.metric_name} ({charter.metric_unit})",
            "target": charter.target,
            "baseline": charter.baseline,
            "channels": ", ".join(plan.experiments[0].channels if plan.experiments else ["N/A"]),
            "duration": charter.time_window_days,
            "cohort_name": plan.target_cohort_name,
            "revenue": report.total_revenue,
            "orders": report.total_orders,
        })

        # Assemble the full playbook template
        playbook = PlaybookTemplate(
            template_id=f"playbook_{plan.target_cohort_name}_{uuid.uuid4().hex[:6]}",
            move_type=result.move_type,
            channels=plan.experiments[0].channels if plan.experiments else [],
            target_icp_labels=result.target_icp_labels,
            description=result.description,
            outcome_charter_template=charter.model_dump(), # In a real system, you'd templatize this
            strike_plan_template=plan.model_dump(), # In a real system, you'd templatize this
            source_strike_plan_id=plan.id,
            key_performance_metrics={
                "total_revenue": f"₹{report.total_revenue:,.2f}",
                "total_orders": str(report.total_orders)
            }
        )
        state['playbook_template'] = playbook
        logger.info(f"  > Successfully generated playbook template: {playbook.template_id}")
        return state

    except Exception as e:
        logger.error(f"  > Error parameterizing playbook: {e}", exc_info=True)
        state['error'] = "The AI failed to summarize the campaign into a playbook."
        return state

def save_playbook_to_archive(state: ArchiveAgentState) -> ArchiveAgentState:
    """Saves the generated playbook into the ChromaDB vector store."""
    logger.info("--- Node: Saving Playbook to Chroma Archive ---")
    if state.get('error'):
        return state
    try:
        playbook = state['playbook_template']
        
        # The text we want to search over
        doc_content = f"Playbook Type: {playbook.move_type}\nDescription: {playbook.description}"
        
        # The structured data we want to store and filter on
        doc_metadata = {
            "template_id": playbook.template_id,
            "channels": ",".join(playbook.channels),
            "target_icp_labels": ",".join(playbook.target_icp_labels),
            "source_strike_plan_id": playbook.source_strike_plan_id,
            # We store the full template as a JSON string in the metadata
            "full_template_json": playbook.model_dump_json()
        }
        
        vs = get_vectorstore()
        if vs is None:
            state['error'] = "ChromaDB service is not running. Please start Chroma and retry."
            return state
        vs.add_documents([Document(page_content=doc_content, metadata=doc_metadata)])
        logger.info(f"  > Successfully saved playbook '{playbook.template_id}' to vector store.")
        return state

    except Exception as e:
        logger.error(f"  > Error saving to ChromaDB: {e}", exc_info=True)
        state['error'] = "Failed to save the new playbook to the template archive."
        return state

# --- RECOMMENDATION AGENT ---

def find_relevant_playbooks(state: RecommendAgentState) -> RecommendAgentState:
    """Uses vector search to find the most relevant existing playbooks for a new goal."""
    logger.info("--- Node: Finding Relevant Playbooks ---")
    try:
        # Find the top 3 most similar playbooks from the archive
        vs = get_vectorstore()
        if vs is None:
            state['error'] = "ChromaDB service is not running. Please start Chroma and retry."
            return state
        retrieved_docs = vs.similarity_search(state['new_goal'], k=3)
        state['retrieved_docs'] = retrieved_docs
        logger.info(f"  > Retrieved {len(retrieved_docs)} relevant playbooks from the archive.")
        return state
    except Exception as e:
        logger.error(f"  > Error retrieving from ChromaDB: {e}", exc_info=True)
        state['error'] = "Failed to search the playbook archive."
        return state

# ... (Recommendation generation node would go here)

# --- Graph Definitions & Runners ---

# Archive Agent
archive_workflow = StateGraph(ArchiveAgentState)
archive_workflow.add_node("parameterize", parameterize_and_summarize)
archive_workflow.add_node("save_to_archive", save_playbook_to_archive)
archive_workflow.set_entry_point("parameterize")
archive_workflow.add_edge("parameterize", "save_to_archive")
archive_workflow.add_edge("save_to_archive", END)
archive_agent_graph = archive_workflow.compile()

async def run_archive_agent(strike_plan: dict, charter: dict, report: dict) -> dict:
    logger.info("--- Running Template Archive Agent ---")
    try:
        initial_state = {
            "strike_plan": StrikePlan(**strike_plan),
            "outcome_charter": OutcomeCharter(**charter),
            "attribution_report": AttributionReport(**report),
        }
        final_state = await archive_agent_graph.ainvoke(initial_state)
        if final_state.get('error'):
            return {"error": final_state['error']}
        return {"status": "success", "template": final_state['playbook_template'].model_dump()}
    except Exception as e:
        logger.error(f"  > Critical error running archive agent: {e}", exc_info=True)
        return {"error": "A critical error occurred while setting up the archive agent."}

# Recommendation Agent (simplified for now)
async def run_recommendation_agent(new_goal: str) -> dict:
    logger.info("--- Running Next Move Recommendation Agent ---")
    # This is a simplified version; a full LangGraph implementation would be similar to the above.
    state = find_relevant_playbooks({"new_goal": new_goal})
    if state.get('error'):
        return {"error": state.get('error')}
    
    # In a full implementation, you'd pass these docs to another LLM node to synthesize a recommendation.
    # For now, we'll just return the most similar document.
    if not state['retrieved_docs']:
        return {"recommendation": "No relevant playbooks found in the archive."}
        
    top_doc = state['retrieved_docs'][0]
    recommendation = NextMoveRecommendation(
        recommended_template_id=top_doc.metadata.get('template_id', 'N/A'),
        recommendation_reason=f"This playbook is recommended because its description is most similar to your goal. Description: {top_doc.page_content}",
        confidence_score=0.85 # Placeholder
    )
    return {"recommendation": recommendation.model_dump()}
