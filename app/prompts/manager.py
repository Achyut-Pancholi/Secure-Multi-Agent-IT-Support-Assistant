from typing import Any, Dict, Optional
from langchain_core.prompts import ChatPromptTemplate
from app.config import settings
from app.observability.logging import get_logger

logger = get_logger(__name__)

from app.prompts.agents.triage import TRIAGE_PROMPT
from app.prompts.agents.knowledge import KNOWLEDGE_PROMPT
from app.prompts.agents.action import ACTION_PROMPT
from app.prompts.agents.response import RESPONSE_PROMPT

# Fallback local prompts in case Langfuse is not configured or prompt is not created yet
LOCAL_PROMPTS = {
    "triage_agent": TRIAGE_PROMPT,
    "knowledge_agent": KNOWLEDGE_PROMPT,
    "action_agent": ACTION_PROMPT,
    "response_agent": RESPONSE_PROMPT
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
