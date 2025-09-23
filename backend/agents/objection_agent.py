import json
import logging
from typing import TypedDict, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.objection_schemas import Objection
from schemas.positioning_schemas import PositioningOptionCard

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
# Fast model for classification and minor edits
def _get_fast_llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model=settings.OLLAMA_FAST_MODEL, temperature=0, format="json", base_url=settings.OLLAMA_BASE_URL)
# Reasoning model for complex reframing tasks
def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.3, base_url=settings.OLLAMA_BASE_URL)


# --- Agent State ---
class ObjectionAgentState(TypedDict):
    """Defines the state for the objection handling graph. Tracks the entire process."""
    original_card: PositioningOptionCard
    objection_text: str
    classified_objection: Objection | None
    revised_card: PositioningOptionCard | None
    clarification_question: str | None
    final_message: str
    error: str | None
    is_fatal_error: bool


# --- Pydantic Models for Structured LLM Outputs (Tools) ---
class ObjectionClassifier(BaseModel):
    """
    Classify the user's objection into a specific type and severity.
    This structure ensures the LLM provides predictable output.
    """
    objection_type: Literal[
        "price", "proof", "relevance", "taboo", "complexity", "competitor", "compliance", "other"
    ] = Field(description="The primary category of the founder's objection.")
    severity: Literal["critical", "minor"] = Field(
        description="The severity. 'critical' for fundamental issues (price, proof, core idea), 'minor' for stylistic tweaks (wording, tone)."
    )
    summary: str = Field(description="A one-sentence summary of the core issue raised by the founder.")


class RevisedCard(BaseModel):
    """
    A tool for the LLM to output a fully revised PositioningOptionCard.
    This ensures the output is always a valid card structure.
    """
    updated_card: PositioningOptionCard = Field(description="The complete, updated positioning card in JSON format.")
    explanation: str = Field(
        description="A concise, friendly message to the founder explaining the specific changes made and the reasoning behind them."
    )


# --- Agent Nodes ---

def classify_objection(state: ObjectionAgentState) -> ObjectionAgentState:
    """
    Node 1: Takes the raw user objection and classifies it using the fast LLM.
    """
    logger.info("--- Node: Classifying Objection ---")
    try:
        classifier_tool = _get_fast_llm().with_structured_output(ObjectionClassifier)

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a meticulous analyst. Your task is to classify founder feedback on a marketing positioning card. "
             "Analyze the user's objection and precisely classify its type and severity based on the provided schema. \n"
             "- 'critical' objections are fundamental problems: 'This price is 50% too high', 'We absolutely cannot make that claim legally', 'That's our main competitor's tagline'.\n"
             "- 'minor' objections are stylistic: 'I don't love the word 'synergy'', 'Can we make the tagline sound more modern?', 'The color palette feels off'.\n"
             "Provide a concise summary of the core issue."),
            ("human", "Here is the positioning card being discussed:\n"
                      "```json\n{card}\n```\n\n"
                      "Here is the founder's raw objection: '{objection}'")
        ])

        chain = prompt | classifier_tool
        result = chain.invoke({
            "card": state['original_card'].model_dump_json(),
            "objection": state['objection_text']
        })

        classified_obj = Objection(
            text=state['objection_text'],
            type=result.objection_type,
            severity=result.severity
        )
        state['classified_objection'] = classified_obj
        logger.info(f"  > Objection classified as: {result.objection_type.upper()} ({result.severity.upper()}). Summary: {result.summary}")
        return state

    except Exception as e:
        logger.error(f"  > Error in classification node: {e}")
        state['error'] = "I had trouble understanding the structure of your feedback. Could you please rephrase it?"
        state['is_fatal_error'] = True
        return state


def reframe_critical_objection(state: ObjectionAgentState) -> ObjectionAgentState:
    """
    Node 2 (Critical Path): Uses the powerful reasoning LLM to completely reframe a card
    based on a critical objection.
    """
    logger.info("--- Node: Reframing Critical Objection ---")
    try:
        card_reviser_tool = _get_reasoning_llm().with_structured_output(RevisedCard)
        objection = state['classified_objection']
        card = state['original_card']

        prompt_template = ChatPromptTemplate.from_messages([
            ("system",
             "You are a world-class brand strategist and a creative problem solver. "
             "A founder has raised a CRITICAL objection to a positioning card. Your job is to resolve it intelligently.\n"
             "Follow these steps:\n"
             "1. **Analyze the Root Cause**: Understand the deep strategic issue behind the founder's objection (e.g., brand risk, market mismatch, economic infeasibility).\n"
             "2. **Propose a Solution**: Based on the objection, modify the specific problematic parts of the positioning card. You might need to change a value pillar, rewrite the tagline, or adjust the behavior lever.\n"
             "3. **Maintain Integrity**: Keep the rest of the card's strong points intact. Do not change what isn't broken.\n"
             "4. **Format the Output**: Provide your response using the 'RevisedCard' tool. The 'updated_card' must be the complete, valid JSON of the positioning card. The 'explanation' should be a clear, confident message to the founder explaining what you changed and why it's a better solution."),
            ("human",
             "Original Positioning Card:\n"
             "```json\n{card_json}\n```\n\n"
             "Founder's Critical Objection (Type: {objection_type}): '{objection_text}'\n\n"
             "Now, think step-by-step and provide the revised card and your explanation using the tool.")
        ])

        chain = prompt_template | card_reviser_tool
        result = chain.invoke({
            "card_json": card.model_dump_json(),
            "objection_type": objection.type,
            "objection_text": objection.text
        })

        state['revised_card'] = result.updated_card
        state['final_message'] = result.explanation
        logger.info("  > Successfully generated a revised card for the critical objection.")
        return state

    except Exception as e:
        logger.error(f"  > Error in reframing node: {e}")
        state['error'] = "I tried to revise the card based on your critical feedback but encountered a creative block. This may need human intervention."
        state['is_fatal_error'] = True
        return state


def patch_minor_objection(state: ObjectionAgentState) -> ObjectionAgentState:
    """
    Node 3 (Minor Path): Uses the fast LLM to make small, targeted edits for
    minor objections, like rewording a tagline.
    """
    logger.info("--- Node: Patching Minor Objection ---")
    try:
        # This is a simplified version. A more complex agent could identify which field to edit.
        # For now, we assume most minor objections are about the tagline.
        objection = state['classified_objection']
        card = state['original_card']

        prompt = ChatPromptTemplate.from_template(
            "A founder has a minor objection to this tagline: '{original_tagline}'.\n"
            "Their feedback is: '{objection_text}'.\n"
            "Please provide a new, improved tagline that addresses their feedback. "
            "Respond with only the new tagline text, and nothing else."
        )
        chain = prompt | _get_reasoning_llm() # Use reasoning model for better creative output
        
        new_tagline = chain.invoke({
            "original_tagline": card.tagline,
            "objection_text": objection.text
        }).content.strip().strip('"')

        revised_card = card.copy()
        revised_card.tagline = new_tagline
        
        state['revised_card'] = revised_card
        state['final_message'] = f"Good point. How does this revised tagline sound: \"{new_tagline}\"?"
        logger.info(f"  > Patched minor objection. New tagline: {new_tagline}")
        return state

    except Exception as e:
        logger.error(f"  > Error in patching node: {e}")
        # Fallback for minor patch: just acknowledge
        state['revised_card'] = state['original_card']
        state['final_message'] = f"Thank you for the feedback on '{state['objection_text']}'. I've noted it down. Does the rest of the card work for you?"
        return state


def handle_error(state: ObjectionAgentState) -> ObjectionAgentState:
    """Node 4 (Error Path): Formulates the final error message."""
    logger.info("--- Node: Handling Error ---")
    state['final_message'] = state.get("error", "An unknown error occurred.")
    return state


# --- Conditional Routing Logic ---
def route_by_severity(state: ObjectionAgentState) -> Literal["reframe_critical", "patch_minor", "handle_error"]:
    """The router that directs the graph's flow based on the classification result."""
    logger.info("--- Router: Routing by Severity ---")
    if state.get("is_fatal_error"):
        logger.warning("  > Fatal error detected. Routing to error handler.")
        return "handle_error"
    
    severity = state['classified_objection'].severity
    logger.info(f"  > Routing based on severity: {severity.upper()}")
    if severity == "critical":
        return "reframe_critical"
    else:
        return "patch_minor"


# --- Graph Definition ---
def build_objection_agent_graph():
    """Builds and compiles the LangGraph for the objection agent."""
    workflow = StateGraph(ObjectionAgentState)

    # Add nodes to the graph
    workflow.add_node("classify_objection", classify_objection)
    workflow.add_node("reframe_critical", reframe_critical_objection)
    workflow.add_node("patch_minor", patch_minor_objection)
    workflow.add_node("error_handler", handle_error)

    # Define the graph's flow
    workflow.set_entry_point("classify_objection")
    workflow.add_conditional_edges(
        "classify_objection",
        route_by_severity,
        {
            "reframe_critical": "reframe_critical",
            "patch_minor": "patch_minor",
            "handle_error": "error_handler"
        }
    )

    # All paths lead to an end point
    workflow.add_edge("reframe_critical", END)
    workflow.add_edge("patch_minor", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()

# Compile the graph when the module is loaded
objection_agent_graph = build_objection_agent_graph()


# --- Main Agent Runner Function ---
async def run_objection_agent(request: dict):
    """
    Entrypoint to run the objection agent.
    Takes the API request and returns the final response.
    """
    logger.info(f"--- Running Objection Agent for card: {request['option_card']['one_word']} ---")
    initial_state = {
        "original_card": PositioningOptionCard(**request['option_card']),
        "objection_text": request['objection_text'],
        "is_fatal_error": False
    }

    # Asynchronously invoke the graph
    final_state = await objection_agent_graph.ainvoke(initial_state)

    if final_state.get('error'):
        logger.error(f"  > Agent finished with error: {final_state['final_message']}")
        return {
            "status": "failed",
            "message": final_state['final_message']
        }

    logger.info("  > Agent finished successfully.")
    return {
        "status": "revised",
        "revised_card": final_state.get('revised_card').model_dump() if final_state.get('revised_card') else None,
        "message": final_state.get('final_message')
    }
