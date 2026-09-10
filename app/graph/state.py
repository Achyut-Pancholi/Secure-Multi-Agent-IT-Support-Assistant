from typing import TypedDict, Optional, List, Dict, Any
from app.models import Priority, Route

class SupportState(TypedDict):
    """
    State dictionary for the LangGraph workflow.
    """
    request_id: str
    user_id: str
    user_query: str
    history: Optional[List[Dict[str, str]]]
    
    # Triage outputs
    category: Optional[str]
    priority: Optional[Priority]
    route: Optional[Route]
    
    # Agent/Tool execution results
    agent_outputs: List[str]
    
    # Final output
    final_response: Optional[str]
    
    # Workflow metadata
    errors: List[str]
