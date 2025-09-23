import logging
from typing import TypedDict, List, Literal

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from langchain_ollama.chat_models import ChatOllama
from langgraph.graph import StateGraph, END

from core.config import settings
from services.registry import get_services
from schemas.intake_schemas import IntakeState

# --- Configuration & Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Models ---
def _get_fast_llm() -> ChatOllama:
    try:
        return get_services().llm_fast
    except Exception:
        return ChatOllama(model=settings.OLLAMA_FAST_MODEL, temperature=0, format="json", base_url=settings.OLLAMA_BASE_URL)

def _get_reasoning_llm() -> ChatOllama:
    try:
        return get_services().llm_reasoning
    except Exception:
        return ChatOllama(model=settings.OLLAMA_REASONING_MODEL, temperature=0.3, base_url=settings.OLLAMA_BASE_URL)

# --- Static Data: The Question Library ---
# As per your blueprint, this library holds the strategic probes.
QUESTION_LIBRARY = {
    "Big Idea": "If you could own one single word or phrase in your ideal customer's mind, what would it be and why is now the perfect time for it?",
    "Proof": "Can you share a specific story or metric about a recent customer success? Please include numbers in ₹, percentages, or time saved if possible.",
    "Enemy": "Who or what is the 'villain' your customers complain about? This could be a direct competitor, a frustrating old process, or a common industry problem.",
    "Jobs-to-Be-Done": "Think about the last time a customer 'hired' your product. Can you walk me through the exact moment or situation that made them decide to look for a solution like yours?",
    "Constraints": "What is one marketing channel, tactic, or message that is absolutely off-limits for your brand, and what's the story behind that rule?"
}

# --- Pydantic Models for Structured LLM Outputs (Tools) ---
class IntentClassifier(BaseModel):
    """Classify the user's message into a specific intent."""
    intent: Literal["fact", "claim", "feeling", "tangent", "question"] = Field(
        description="The primary intent of the user's message."
    )
    summary: str = Field(description="A concise one-sentence summary of the user's message.")

class NextQuestionSelector(BaseModel):
    """Select the next best question to ask from the list of missing strategic slots."""
    next_slot_to_probe: str = Field(description="The single best strategic slot to probe next from the list of missing slots.")
    reasoning: str = Field(description="A brief justification for why this is the most logical next question to ask.")

# --- Agent State ---
class IntakeAgentState(TypedDict):
    """
    Defines the state for the intake interview graph. It's the agent's memory.
    """
    history: List[str]
    user_message: str
    missing_slots: List[str]
    last_intent: str | None
    ai_response: str

# --- Agent Nodes ---
def classify_user_intent(state: IntakeAgentState) -> IntakeAgentState:
    """
    Node 1: Takes the user's latest message and classifies its intent using the fast LLM.
    This helps the agent understand what kind of information it just received.
    """
    logger.info("--- Node: Classifying User Intent ---")
    try:
        classifier_tool = _get_fast_llm().with_structured_output(IntentClassifier)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are an expert at classifying a founder's statements during a strategy session. "
             "Analyze the user's message and classify its primary intent using the available tool. "
             "Provide a concise summary."),
            ("human", "Conversation History:\n{history}\n\nUser's latest message: '{user_message}'")
        ])
        
        chain = prompt | classifier_tool
        history_str = "\n".join(state['history'][-4:]) # Use last 4 turns for context
        result = chain.invoke({
            "history": history_str,
            "user_message": state['user_message']
        })
        
        state['last_intent'] = result.intent
        # Here, you could save the summary to a fact-base in ChromaDB
        logger.info(f"  > Intent classified as: {result.intent.upper()}. Summary: {result.summary}")
        return state
    except Exception as e:
        logger.error(f"  > Error in intent classification: {e}")
        state['last_intent'] = "error"
        state['ai_response'] = "I had a bit of trouble processing that. Could we try approaching it differently?"
        return state

def select_next_question(state: IntakeAgentState) -> IntakeAgentState:
    """
    Node 2: The strategic core. Uses the reasoning LLM to decide which question to ask next
    to fill the most critical gap in its knowledge.
    """
    logger.info("--- Node: Selecting Next Question ---")
    
    # If all strategic slots are filled, the interview is over.
    if not state['missing_slots']:
        logger.info("  > All strategic slots are filled. Concluding interview.")
        state['ai_response'] = "This has been incredibly helpful. Thank you. I have all the initial strategic information I need. We can now move on to generating positioning options."
        return state

    try:
        selector_tool = _get_reasoning_llm().with_structured_output(NextQuestionSelector)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You are a Senior Brand Strategist conducting an interview. Your goal is to gather critical strategic information. "
             "Based on the conversation so far, you need to decide which topic to probe next. "
             "Review the remaining 'missing slots' and the conversation history, then select the most logical next topic to explore. "
             "Use the 'NextQuestionSelector' tool to state your choice and reasoning."),
            ("human",
             "Conversation History:\n{history}\n\n"
             "Last user statement was classified as: {last_intent}\n\n"
             "These are the strategic slots we still need to fill: {missing_slots}\n\n"
             "Which one should we probe next and why?")
        ])
        
        chain = prompt | selector_tool
        history_str = "\n".join(state['history'][-6:]) # Use more history for strategic choice
        result = chain.invoke({
            "history": history_str,
            "last_intent": state['last_intent'],
            "missing_slots": ", ".join(state['missing_slots'])
        })

        chosen_slot = result.next_slot_to_probe
        if chosen_slot not in QUESTION_LIBRARY:
            # Fallback if the LLM hallucinates a slot name
            chosen_slot = state['missing_slots'][0]

        question_to_ask = QUESTION_LIBRARY[chosen_slot]
        
        state['ai_response'] = question_to_ask
        state['missing_slots'] = [s for s in state['missing_slots'] if s != chosen_slot]
        logger.info(f"  > Selected question for slot '{chosen_slot}'. Reasoning: {result.reasoning}")
        return state

    except Exception as e:
        logger.error(f"  > Error selecting next question: {e}")
        # If strategic selection fails, fall back to the next question in the list
        chosen_slot = state['missing_slots'][0]
        state['ai_response'] = QUESTION_LIBRARY[chosen_slot]
        state['missing_slots'] = state['missing_slots'][1:]
        return state

# --- Graph Definition ---
def build_intake_agent_graph():
    """Builds and compiles the LangGraph for the intake interview agent."""
    workflow = StateGraph(IntakeAgentState)
    workflow.add_node("classify_intent", classify_user_intent)
    workflow.add_node("select_question", select_next_question)
    workflow.set_entry_point("classify_intent")
    workflow.add_edge("classify_intent", "select_question")
    workflow.add_edge("select_question", END)
    return workflow.compile()

intake_agent_graph = build_intake_agent_graph()


# --- Main Agent Runner Function ---
async def run_intake_agent_turn(user_message: str, history: List[str]) -> str:
    """
    Entrypoint to run a single turn of the intake agent.
    """
    logger.info("--- Running Intake Agent Turn ---")
    
    # Determine which slots are still missing based on the conversation history
    missing_slots = list(QUESTION_LIBRARY.keys())
    for turn in history:
        for slot, question_text in QUESTION_LIBRARY.items():
            # A simple check: if the question was asked, assume the slot is filled.
            if question_text in turn and slot in missing_slots:
                missing_slots.remove(slot)

    initial_state = IntakeAgentState(
        user_message=user_message,
        history=history,
        missing_slots=missing_slots,
        last_intent=None,
        ai_response=""
    )
    
    final_state = await intake_agent_graph.ainvoke(initial_state)
    
    return final_state.get("ai_response", "I'm not sure how to respond to that. Could you rephrase?")
