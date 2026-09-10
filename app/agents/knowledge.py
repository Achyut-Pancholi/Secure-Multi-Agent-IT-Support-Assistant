from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool
from app.config import settings
from app.prompts.manager import PromptProvider
from app.tools.knowledge import search_knowledge_base
from app.guardrails.tool import authorize_tool_call
from app.observability.logging import get_logger

logger = get_logger(__name__)

# Wrap the tool to enforce authorization
def authorized_search_knowledge_base(query: str) -> str:
    authorize_tool_call("knowledge_agent", "search_knowledge_base")
    return search_knowledge_base.invoke({"query": query})

auth_knowledge_tool = StructuredTool.from_function(
    func=authorized_search_knowledge_base,
    name="search_knowledge_base",
    description="Search the internal IT support knowledge base for troubleshooting guidance. Provide a specific query to find relevant articles."
)

class KnowledgeAgent:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.0
        )
        self.prompt_provider = PromptProvider()
        self.tools = [auth_knowledge_tool]
        
    def execute(self, query: str) -> str:
        logger.info(f"KnowledgeAgent executing query: {query}")
        
        prompt_template = self.prompt_provider.get_prompt("knowledge_agent")
        system_instruction = prompt_template.messages[0].prompt.template.replace("{query}", query)
        
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=system_instruction
        )
        
        result = agent.invoke({
            "messages": [HumanMessage(content=query)]
        })
        
        # Get the final message content
        final_message = result["messages"][-1]
        return final_message.content
