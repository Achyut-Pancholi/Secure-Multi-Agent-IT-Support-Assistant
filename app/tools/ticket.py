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

@tool
def update_support_ticket(user_id: str, ticket_id: str, description: str = None, category: str = None, priority: str = None, status: str = None) -> str:
    """
    Update an existing support ticket in the internal IT system.
    Use this when you need to escalate a priority, change the status, or append/update information on an existing ticket.
    """
    logger.info(f"Executing update_support_ticket for ticket: {ticket_id}")
    try:
        updates = {}
        if description is not None: updates["description"] = description
        if category is not None: updates["category"] = category
        if priority is not None: updates["priority"] = priority
        if status is not None: updates["status"] = status
        
        data = client.update_ticket(ticket_id, updates)
        
        # --- CODE BASED STATE EXTRACTION (0 LLM Cost) ---
        from app.memory.long_term import get_user_memory, save_user_memory
        mem = get_user_memory(user_id)
        ticket_history = mem.get("ticket_history", [])
        
        # Update it in the memory array
        for t in ticket_history:
            if t.get("ticket_id") == ticket_id:
                if description is not None: t["issue"] = description
                if category is not None: t["category"] = category
                if priority is not None: t["priority"] = priority
                if status is not None: t["status"] = status
                
        mem["ticket_history"] = ticket_history
        save_user_memory(user_id, mem)
        # ------------------------------------------------
        
        return json.dumps(data, indent=2)
    except InternalAPIError as e:
        return f"Error updating ticket: {str(e)}"

