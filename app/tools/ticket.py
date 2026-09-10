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
        return json.dumps(data, indent=2)
    except InternalAPIError as e:
        return f"Error creating ticket: {str(e)}"

