from mcp.server.fastmcp import FastMCP
from app.tools.knowledge import search_knowledge_base
from app.tools.access import check_user_access
from app.tools.service import check_service_status
from app.tools.ticket import create_support_ticket

# Initialize FastMCP Server
mcp = FastMCP("IT Support MCP Server")

@mcp.tool()
def mcp_search_knowledge_base(query: str) -> str:
    """Search the internal IT support knowledge base for troubleshooting guidance."""
    return search_knowledge_base.invoke({"query": query})

@mcp.tool()
def mcp_check_user_access(user_id: str) -> str:
    """Check the current access permissions and roles for a specific user."""
    return check_user_access.invoke({"user_id": user_id})

@mcp.tool()
def mcp_check_service_status(service_name: str) -> str:
    """Check the current operational status of an internal IT service (e.g., 'vpn', 'finance_db')."""
    return check_service_status.invoke({"service_name": service_name})

@mcp.tool()
def mcp_create_support_ticket(user_id: str, description: str, category: str, priority: str) -> str:
    """Create a new support ticket in the internal IT system."""
    return create_support_ticket.invoke({
        "user_id": user_id,
        "description": description,
        "category": category,
        "priority": priority
    })

if __name__ == "__main__":
    # This exposes the MCP tools over stdio. Run via:
    # python -m app.mcp.server
    mcp.run()

