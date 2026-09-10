from langchain_groq import ChatGroq
from app.config import settings
from app.prompts.manager import PromptProvider
from app.models import TriageResult
from app.observability.logging import get_logger, get_langfuse_callback

logger = get_logger(__name__)

class TriageAgent:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.1
        )
        self.prompt_provider = PromptProvider()
        
    def classify(self, query: str) -> TriageResult:
        logger.info(f"TriageAgent classifying query: {query}")
        
        prompt = self.prompt_provider.get_prompt("triage_agent")
        
        # Use structured output for triage
        structured_llm = self.llm.with_structured_output(TriageResult)
        
        chain = prompt | structured_llm
        
        callbacks = []
        lf_callback = get_langfuse_callback()
        if lf_callback:
            callbacks.append(lf_callback)
            
        result = chain.invoke({"query": query}, config={"callbacks": callbacks})
        
        logger.info(f"Triage Result: Route={result.route}, Priority={result.priority}")
        return result

