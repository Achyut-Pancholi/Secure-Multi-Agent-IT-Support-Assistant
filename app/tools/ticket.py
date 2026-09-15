import json
from langchain_core.tools import tool
from app.clients.internal_api import InternalAPIClient, InternalAPIError
from app.observability.logging import get_logger

logger = get_logger(__name__)
client = InternalAPIClient()

@tool
def create_support_ticket(user_id: str, description: str, category: str, priority: str) -> str:
    """
    Create a new support ticket in the internal IT system.
    Only use this if the issue cannot be resolved through guidance, or if explicit manual intervention is required.
    """
    logger.info(f"Executing create_support_ticket for user: {user_id}")
    try:
        data = client.create_ticket(user_id, description, category, priority)
        # --- CODE BASED STATE EXTRACTION (0 LLM Cost) ---
        from app.memory.long_term import get_user_memory, save_user_memory
        if "ticket_id" in data:
            mem = get_user_memory(user_id)
            
            # 1. Append to known_issues
            known_issues = mem.get("known_issues", [])
            if description not in known_issues:
                known_issues.append(description)
            mem["known_issues"] = known_issues
            
            # 2. Append to ticket_history array
            ticket_history = mem.get("ticket_history", [])
            ticket_history.append({
                "ticket_id": data["ticket_id"],
                "issue": description,
                "category": category,
                "priority": priority
            })
            mem["ticket_history"] = ticket_history
            
            # Save back to SQLite
            save_user_memory(user_id, mem)
        # ------------------------------------------------
        return json.dumps(data, indent=2)
    except InternalAPIError as e:
        return f"Error creating ticket: {str(e)}"

