from langgraph.graph import StateGraph, END
from app.graph.state import SupportState
from app.agents.triage import TriageAgent
from app.agents.knowledge import KnowledgeAgent
from app.agents.action import ActionAgent
from app.agents.response import ResponseAgent
from app.guardrails.input import validate_input
from app.guardrails.output import validate_output
from app.models import Route
from app.observability.logging import get_logger

logger = get_logger(__name__)

# Initialize agents
triage_agent = TriageAgent()
knowledge_agent = KnowledgeAgent()
action_agent = ActionAgent()
response_agent = ResponseAgent()

from app.memory.long_term import get_user_memory

def build_conversation_context(state: SupportState) -> str:
    """
    Combines conversation history with the current query so agents have full context.
    Uses Lazy Summarization for long histories and injects SQLite long-term facts.
    """
    # 1. Fetch code-based state facts from long-term memory (SQLite)
    user_mem = get_user_memory(state["user_id"])
    mem_str = f"SYSTEM KNOWLEDGE (User Facts): {user_mem}\n\n" if user_mem else ""

    history = state.get("history") or []
    if not history:
        return mem_str + state["user_query"]
        
    history_lines = []
    
    # 2. Lazy Summarization logic (Rolling Context)
    if len(history) > 4:
        older_messages = history[:-4]
        try:
            from langchain_groq import ChatGroq
            from langchain_core.messages import HumanMessage, SystemMessage
            from app.config import settings
            
            # Format older messages
            chat_text = "\n".join([f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}" for m in older_messages])
            
            # Fast, structured summarization call
            llm = ChatGroq(api_key=settings.groq_api_key, model_name=settings.groq_model, temperature=0.1, max_tokens=250)
            sys_prompt = (
                "You are a memory compressor. Summarize the older conversation history into a highly dense, bulleted list. "
                "Include:\n"
                "- Core issues raised by the user\n"
                "- Actions/resolutions taken by the agent\n"
                "- Important facts, IDs, or constraints mentioned\n"
                "Output strictly bullet points."
            )
            
            res = llm.invoke([SystemMessage(content=sys_prompt), HumanMessage(content=chat_text)])
            summary = res.content.strip()
            
            history_lines.append(f"--- LAZY SUMMARY OF OLDER CHAT ---\n{summary}\n----------------------------------")
        except Exception as e:
            history_lines.append(f"[LAZY SUMMARY OF OLDER CHAT]: (Summarization failed: {e})")
            
    # Take the last 4 messages for relevant context
    for msg in history[-4:]:
        role = msg.get("role", "user").capitalize()
        content = msg.get("content", "")
        history_lines.append(f"{role}: {content}")
        
    history_str = "\n".join(history_lines)
    return f"{mem_str}Previous Conversation:\n{history_str}\n\nLatest User Message: {state['user_query']}"


def node_input_guardrail(state: SupportState):
    logger.info("Executing node: input_guardrail")
    try:
        valid_query = validate_input(state["user_query"], state["user_id"])
        return {"user_query": valid_query}
    except ValueError as e:
        logger.warning(f"Input validation failed: {str(e)}")
        return {"errors": state.get("errors", []) + [str(e)]}

def node_triage(state: SupportState):
    logger.info("Executing node: triage_agent")
    if state.get("errors"):
        return state
        
    # Provide conversation history to triage so follow-ups like 'yes' are routed correctly
    context_query = build_conversation_context(state)
    result = triage_agent.classify(context_query)
    return {
        "category": result.category,
        "priority": result.priority,
        "route": result.route
    }

def node_knowledge(state: SupportState):
    logger.info("Executing node: knowledge_agent")
    output = knowledge_agent.execute(state["user_query"])
    return {"agent_outputs": state.get("agent_outputs", []) + [f"Knowledge Agent: {output}"]}

def node_action(state: SupportState):
    logger.info("Executing node: action_agent")
    # Action agent receives user ID and conversation context to perform tickets/access checks
    context_query = f"User ID: {state['user_id']}\n{build_conversation_context(state)}"
    output = action_agent.execute(context_query)
    return {"agent_outputs": state.get("agent_outputs", []) + [f"Action Agent: {output}"]}

def node_response(state: SupportState):
    logger.info("Executing node: response_agent")
    if state.get("errors"):
        error_msg = " ".join(state["errors"])
        return {"final_response": f"I cannot process your request. {error_msg}"}
        
    context = "\n".join(state.get("agent_outputs", []))
    output = response_agent.generate(build_conversation_context(state), context)
    return {"final_response": output}

def node_output_guardrail(state: SupportState):
    logger.info("Executing node: output_guardrail")
    final_output = state.get("final_response", "")
    safe_output = validate_output(final_output)
    return {"final_response": safe_output}

def route_request(state: SupportState):
    logger.info(f"Routing request based on route: {state.get('route')}")
    if state.get("errors"):
        return "response_agent"
        
    route = state.get("route")
    if route == Route.KNOWLEDGE:
        return "knowledge_agent"
    elif route == Route.ACTION:
        return "action_agent"
    else:
        return "response_agent"

def build_workflow() -> StateGraph:
    workflow = StateGraph(SupportState)
    
    # Add nodes
    workflow.add_node("input_guardrail", node_input_guardrail)
    workflow.add_node("triage_agent", node_triage)
    workflow.add_node("knowledge_agent", node_knowledge)
    workflow.add_node("action_agent", node_action)
    workflow.add_node("response_agent", node_response)
    workflow.add_node("output_guardrail", node_output_guardrail)
    
    # Add edges
    workflow.set_entry_point("input_guardrail")
    workflow.add_edge("input_guardrail", "triage_agent")
    
    # Conditional routing after triage
    workflow.add_conditional_edges(
        "triage_agent",
        route_request,
        {
            "knowledge_agent": "knowledge_agent",
            "action_agent": "action_agent",
            "response_agent": "response_agent"
        }
    )
    
    workflow.add_edge("knowledge_agent", "response_agent")
    workflow.add_edge("action_agent", "response_agent")
    
    workflow.add_edge("response_agent", "output_guardrail")
    workflow.add_edge("output_guardrail", END)
    
    return workflow.compile()
