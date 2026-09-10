from typing import List
from app.observability.logging import get_logger

logger = get_logger(__name__)

class AuthorizationError(Exception):
    pass

# Define tool policies per agent type
TOOL_POLICY = {
    "knowledge_agent": ["search_knowledge_base"],
    "action_agent": ["check_user_access", "check_service_status", "create_support_ticket"],
    "triage_agent": [], # Triage shouldn't execute tools
    "response_agent": [] # Response shouldn't execute tools
}

def authorize_tool_call(agent_name: str, tool_name: str) -> bool:
    """
    Authorizes whether a specific agent is allowed to execute a specific tool.
    Raises AuthorizationError if denied.
    """
    allowed_tools = TOOL_POLICY.get(agent_name, [])
    
    if tool_name in allowed_tools:
        logger.info(f"Tool authorization GRANTED: Agent '{agent_name}' -> Tool '{tool_name}'")
        return True
        
    logger.warning(f"Tool authorization DENIED: Agent '{agent_name}' -> Tool '{tool_name}'")
    raise AuthorizationError(f"Agent '{agent_name}' is not authorized to use tool '{tool_name}'")

