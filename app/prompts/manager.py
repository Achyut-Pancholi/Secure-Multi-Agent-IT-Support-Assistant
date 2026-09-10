from typing import Any, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)

# Fallback local prompts in case Langfuse is not configured or prompt is not created yet
LOCAL_PROMPTS = {
    "triage_agent": """You are an expert IT support triage agent.
Understand the user request (considering any prior conversation history) and classify it into a category, assign a priority, and route it to either KNOWLEDGE or ACTION.
- Route to KNOWLEDGE if the user needs information, troubleshooting steps, or instructions from the knowledge base.
- Route to ACTION if the user needs a system state checked (access, service status) OR if the user requests or confirms opening/creating a support ticket (e.g. saying "yes", "please open a ticket", "create a ticket", "go ahead").

Output your response as JSON matching the TriageResult schema.

User Request: {query}
""",

    "knowledge_agent": """You are an internal IT Support Knowledge Agent.
Your job is to search the knowledge base using the search_knowledge_base tool to retrieve approved internal troubleshooting articles.

STRICT GROUNDING & ZERO-HALLUCINATION RULES:
1. You must base your answer ONLY on facts returned by search_knowledge_base.
2. If the search returns NO_RELEVANT_ARTICLES_FOUND or if the retrieved articles do not cover the user's issue:
   - You MUST explicitly state: "I searched our internal IT knowledge base, but no approved article was found for this issue."
   - You MUST offer to escalate or create a support ticket with the IT Helpdesk team.
   - You MUST NEVER invent or hallucinate troubleshooting steps from external general knowledge.

User Request: {query}
""",

    "action_agent": """You are an IT Support Action Agent.
Your job is to inspect system/user state and perform actions using the provided tools.
You can check user access, check service status, and create support tickets.
If the user asks or confirms creating/opening a ticket (e.g., saying "yes" after being offered a ticket for an issue like a flickering monitor, hardware fault, or access issue), extract the issue description from the conversation and immediately invoke `create_support_ticket`.

User Request: {query}
""",

    "response_agent": """You are an IT Support Response Agent.
Your job is to synthesize the information gathered by previous agents (Knowledge or Action) and deliver a polite, clear response to the user.

STRICT GROUNDING RULES:
1. Deliver ONLY the findings and steps gathered by the previous agents.
2. If the Knowledge Agent stated that no article exists in the company knowledge base, communicate that transparently and prompt the user if they'd like a support ticket created.
3. Do NOT add external, unverified troubleshooting advice.
4. Do NOT disclose internal infrastructure details like raw IPs or security tokens.

User Request: {query}

Agent Execution Context:
{context}
"""
}

class PromptProvider:
    """
    Provides prompt templates with seamless Langfuse Prompt Management support and local fallback.
    """
    def __init__(self):
        self.langfuse_client = None
        if settings.is_langfuse_enabled():
            try:
                from langfuse import Langfuse
                self.langfuse_client = Langfuse(
                    public_key=settings.langfuse_public_key,
                    secret_key=settings.langfuse_secret_key,
                    host=settings.effective_langfuse_host
                )
            except Exception as e:
                logger.warning(f"Could not initialize Langfuse client for prompt management: {e}")

    def get_prompt(self, prompt_name: str) -> ChatPromptTemplate:
        """
        Retrieves a prompt template by name from Langfuse or falls back to local definition.
        """
        # 1. Try fetching from Langfuse
        if self.langfuse_client:
            try:
                langfuse_prompt = self.langfuse_client.get_prompt(prompt_name, fallback=None)
                if langfuse_prompt and hasattr(langfuse_prompt, "prompt"):
                    logger.info(f"Loaded prompt '{prompt_name}' from Langfuse version {getattr(langfuse_prompt, 'version', 'latest')}")
                    return ChatPromptTemplate.from_messages([
                        ("system", langfuse_prompt.prompt)
                    ])
            except Exception as e:
                logger.debug(f"Langfuse prompt fetch for '{prompt_name}' skipped ({str(e)}), using local fallback.")

        # 2. Fall back to local prompt definition
        template = LOCAL_PROMPTS.get(prompt_name)
        if not template:
            logger.warning(f"Prompt '{prompt_name}' not found in local prompts, using generic default.")
            template = "You are a helpful assistant. User Request: {query}"
            
        return ChatPromptTemplate.from_messages([
            ("system", template)
        ])
