from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from app.config import settings
from app.prompts.manager import PromptProvider
from app.tools.access import check_user_access
from app.tools.service import check_service_status
from app.tools.ticket import create_support_ticket, update_support_ticket
from app.guardrails.tool import authorize_tool_call
from app.observability.logging import get_logger

logger = get_logger(__name__)

from typing import Optional
from pydantic import BaseModel, Field

# Define explicit schemas for all tools
class CheckUserAccessInput(BaseModel):
    user_id: str = Field(description="The unique user ID to check permissions for, e.g. 'user123' or 'user456'")

class CheckServiceStatusInput(BaseModel):
    service_name: str = Field(description="The IT service name to inspect, e.g. 'vpn', 'finance_db'")

class CreateTicketInput(BaseModel):
    user_id: str = Field(description="The user ID requesting the ticket, e.g. 'user123'")
    description: str = Field(description="Detailed summary of the IT issue")
    category: str = Field(description="Ticket category, e.g. 'Hardware', 'Network', 'Software'")
    priority: str = Field(description="Ticket priority level: 'Low', 'Medium', or 'High'")

class UpdateTicketInput(BaseModel):
    user_id: str = Field(description="The user ID requesting the update")
    ticket_id: str = Field(description="The ticket identifier to update, e.g. 'TKT-1000' or '1000'")
    description: Optional[str] = Field(default=None, description="Updated issue description (optional)")
    category: Optional[str] = Field(default=None, description="Updated category e.g. 'Hardware', 'Network', 'Software' (optional)")
    priority: Optional[str] = Field(default=None, description="Updated priority e.g. 'Low', 'Medium', 'High' (optional)")
    status: Optional[str] = Field(default=None, description="Updated status e.g. 'open', 'in_progress', 'Closed', 'reopened' (optional)")

# Wrap tools to enforce authorization
def authorized_check_user_access(user_id: str) -> str:
    authorize_tool_call("action_agent", "check_user_access")
    return check_user_access.invoke({"user_id": user_id})

def authorized_check_service_status(service_name: str) -> str:
    authorize_tool_call("action_agent", "check_service_status")
    return check_service_status.invoke({"service_name": service_name})

def authorized_create_support_ticket(user_id: str, description: str, category: str, priority: str) -> str:
    authorize_tool_call("action_agent", "create_support_ticket")
    return create_support_ticket.invoke({
        "user_id": user_id, 
        "description": description, 
        "category": category, 
        "priority": priority
    })

def authorized_update_support_ticket(user_id: str, ticket_id: str, description: Optional[str] = None, category: Optional[str] = None, priority: Optional[str] = None, status: Optional[str] = None) -> str:
    authorize_tool_call("action_agent", "update_support_ticket")
    return update_support_ticket.invoke({
        "user_id": user_id,
        "ticket_id": ticket_id,
        "description": description,
        "category": category,
        "priority": priority,
        "status": status
    })

auth_tools = [
    StructuredTool.from_function(
        func=authorized_check_user_access,
        name="check_user_access",
        description="Check the current access permissions and roles for a specific user.",
        args_schema=CheckUserAccessInput
    ),
    StructuredTool.from_function(
        func=authorized_check_service_status,
        name="check_service_status",
        description="Check the current operational status of an internal IT service (e.g., 'vpn', 'finance_db').",
        args_schema=CheckServiceStatusInput
    ),
    StructuredTool.from_function(
        func=authorized_create_support_ticket,
        name="create_support_ticket",
        description="Create a new support ticket in the internal IT system.",
        args_schema=CreateTicketInput
    ),
    StructuredTool.from_function(
        func=authorized_update_support_ticket,
        name="update_support_ticket",
        description="Update an existing support ticket in the internal IT system. Can change description, priority, category, or status.",
        args_schema=UpdateTicketInput
    )
]

class ActionAgent:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.2
        )
        self.prompt_provider = PromptProvider()
        self.tools = auth_tools
        
    def execute(self, query: str) -> str:
        logger.info(f"ActionAgent executing query: {query}")
        
        prompt_template = self.prompt_provider.get_prompt("action_agent")
        system_instruction = prompt_template.messages[0].prompt.template.replace("{query}", query)
        
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_instruction
        )
        
        result = agent.invoke({
            "messages": [HumanMessage(content=query)]
        })
        
        final_message = result["messages"][-1]
        return final_message.content
