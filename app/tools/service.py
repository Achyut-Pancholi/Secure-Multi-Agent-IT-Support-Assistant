import json
from langchain_core.tools import tool
from app.clients.internal_api import InternalAPIClient, InternalAPIError
from app.observability.logging import get_logger

logger = get_logger(__name__)
client = InternalAPIClient()

@tool
def check_service_status(service_name: str) -> str:
    """
    Check the current operational status of an internal IT service (e.g., 'vpn', 'finance_db').
    """
    logger.info(f"Executing check_service_status for service: {service_name}")
    try:
        data = client.get_service_status(service_name)
        return json.dumps(data, indent=2)
    except InternalAPIError as e:
        return f"Error checking service status: {str(e)}"

