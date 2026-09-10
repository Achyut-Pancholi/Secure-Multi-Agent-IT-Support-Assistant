import json
import os
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.observability.logging import get_logger

logger = get_logger(__name__)

KB_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge", "kb.json")
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge", "chroma_db")

# Initialize embeddings
try:
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
except Exception as e:
    logger.error(f"Failed to load HuggingFaceEmbeddings: {e}")
    embeddings = None

vector_store = None

def init_chroma():
    global vector_store
    if not embeddings:
        return
    
    if os.path.exists(CHROMA_DB_PATH) and os.listdir(CHROMA_DB_PATH):
        logger.info("Loading existing Chroma DB.")
        vector_store = Chroma(persist_directory=CHROMA_DB_PATH, embedding_function=embeddings)
    else:
        logger.info("Initializing new Chroma DB from kb.json.")
        if not os.path.exists(KB_JSON_PATH):
            logger.warning("kb.json not found. Chroma DB will be empty.")
            return
        with open(KB_JSON_PATH, "r") as f:
            kb_data = json.load(f)
        
        texts = [f"{item['title']}\n{item['content']}" for item in kb_data]
        metadatas = [{"id": item["id"], "tags": ",".join(item["tags"])} for item in kb_data]
        
        vector_store = Chroma.from_texts(
            texts=texts,
            metadatas=metadatas,
            embedding=embeddings,
            persist_directory=CHROMA_DB_PATH
        )

init_chroma()

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the internal IT support knowledge base for official troubleshooting articles.
    Provide a specific query to find relevant articles.
    """
    logger.info(f"Executing search_knowledge_base with query: {query}")
    
    if not vector_store:
        return "Knowledge base vector store is unavailable."
        
    # Search with distance score (lower score = higher similarity)
    results_with_score = vector_store.similarity_search_with_score(query, k=2)
    
    # Filter out irrelevant matches (Chroma distance threshold > 1.2 is considered irrelevant)
    relevant_results = []
    for doc, score in results_with_score:
        if score < 1.15:
            relevant_results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": round(float(score), 4)
            })
            
    if not relevant_results:
        return "NO_RELEVANT_ARTICLES_FOUND: No approved IT knowledge base article exists for this specific issue."
        
    return json.dumps(relevant_results, indent=2)
