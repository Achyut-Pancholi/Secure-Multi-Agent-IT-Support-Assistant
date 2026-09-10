import json
from langchain_core.tools import tool
from app.clients.internal_api import InternalAPIClient, InternalAPIError
from app.observability.logging import get_logger

logger = get_logger(__name__)
client = InternalAPIClient()

@tool
def check_user_access(user_id: str) -> str:
    """
    Check the current access permissions and roles for a specific user.
    """
    logger.info(f"Executing check_user_access for user: {user_id}")
    try:
        data = client.get_user_access(user_id)
        return json.dumps(data, indent=2)
    except InternalAPIError as e:
        return f"Error checking access: {str(e)}"

