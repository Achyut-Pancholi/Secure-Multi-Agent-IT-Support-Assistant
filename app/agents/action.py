from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from app.config import settings
from app.prompts.manager import PromptProvider
from app.tools.access import check_user_access
from app.tools.service import check_service_status
from app.tools.ticket import create_support_ticket
from app.guardrails.tool import authorize_tool_call
from app.observability.logging import get_logger

logger = get_logger(__name__)

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

auth_tools = [
    StructuredTool.from_function(
        func=authorized_check_user_access,
        name="check_user_access",
        description="Check the current access permissions and roles for a specific user."
    ),
    StructuredTool.from_function(
        func=authorized_check_service_status,
        name="check_service_status",
        description="Check the current operational status of an internal IT service (e.g., 'vpn', 'finance_db')."
    ),
    StructuredTool.from_function(
        func=authorized_create_support_ticket,
        name="create_support_ticket",
        description="Create a new support ticket in the internal IT system."
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
