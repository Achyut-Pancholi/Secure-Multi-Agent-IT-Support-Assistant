from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser
from app.config import settings
from app.prompts.manager import PromptProvider
from app.observability.logging import get_logger, get_langfuse_callback

logger = get_logger(__name__)

class ResponseAgent:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model_name=settings.groq_model,
            temperature=0.0
        )
        self.prompt_provider = PromptProvider()
        
    def generate(self, query: str, context: str) -> str:
        logger.info(f"ResponseAgent generating response.")
        
        prompt = self.prompt_provider.get_prompt("response_agent")
        chain = prompt | self.llm | StrOutputParser()
        
        callbacks = []
        lf_callback = get_langfuse_callback()
        if lf_callback:
            callbacks.append(lf_callback)
            
        result = chain.invoke(
            {"query": query, "context": context}, 
            config={"callbacks": callbacks}
        )
        
        return result

