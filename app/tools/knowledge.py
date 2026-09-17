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
    
    if not os.path.exists(KB_JSON_PATH):
        logger.warning("kb.json not found. Chroma DB will be empty.")
        return
        
    with open(KB_JSON_PATH, "r") as f:
        kb_data = json.load(f)
    
    texts = [f"{item['title']}\n{item['content']}" for item in kb_data]
    metadatas = [{"id": item["id"], "tags": ",".join(item["tags"])} for item in kb_data]
    ids = [item["id"] for item in kb_data]
    
    vector_store = Chroma(
        persist_directory=CHROMA_DB_PATH,
        embedding_function=embeddings
    )
    
    # Check for missing articles from kb.json and sync them
    existing_ids = set()
    try:
        existing_data = vector_store.get()
        if existing_data and "ids" in existing_data:
            existing_ids = set(existing_data["ids"])
    except Exception as e:
        logger.warning(f"Could not retrieve existing Chroma IDs: {e}")

    new_texts, new_metadatas, new_ids = [], [], []
    for t, m, i in zip(texts, metadatas, ids):
        if i not in existing_ids:
            new_texts.append(t)
            new_metadatas.append(m)
            new_ids.append(i)

    if new_texts:
        logger.info(f"Syncing {len(new_texts)} new articles from kb.json into Chroma DB.")
        vector_store.add_texts(texts=new_texts, metadatas=new_metadatas, ids=new_ids)

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
