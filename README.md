# Secure Multi-Agent IT Support Assistant

An internal IT Support Assistant Proof of Concept demonstrating a modular monolithic architecture, multi-agent orchestration via LangGraph, and secure tool execution.

## Features
- **Triage, Knowledge, Action, Response Agents**
- **Strict Tool Guardrails**
- **Local SQLite Memory**
- **LangGraph Workflow Orchestration**
- **Streaming Responses (SSE) and WebSocket support**
- **Zero-Cost Local Architecture** (except for LLM which uses Groq OSS models)
- **Observability** (Logging, Metrics, Langfuse traces)
- **Local Embeddings & RAG**: HuggingFace Embeddings stored persistently via Chroma DB.

## Architecture Overview
The application is built as a Modular Monolith.
- **API**: FastAPI for handling user requests.
- **Graph**: LangGraph defining the AI workflow.
- **Agents**: Separate modules with distinct reasoning responsibilities.
- **Tools & Guardrails**: Strict policy execution limiting agent capabilities.

See [docs/architecture.md](docs/architecture.md) for details.

## Dependencies (Zero-Cost Local)
- **Database**: SQLite (Local)
- **Embeddings**: HuggingFace `sentence-transformers` & Chroma DB (Local)
- **UI**: Streamlit (Local)
- **API**: FastAPI (Local)
- **LLM**: Groq API (Uses OSS models like Llama 3.1. Requires API Key, but free tier is available)
- **Observability**: Langfuse (Can be hosted locally via Docker)

## Setup
1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies: `pip install -r requirements.txt`
4. Copy `.env.example` to `.env` and configure your `GROQ_API_KEY`.

### Local Langfuse (Optional)
You can run Langfuse locally to inspect LLM traces:
```bash
# Clone langfuse repository
git clone https://github.com/langfuse/langfuse.git
cd langfuse

# Start with docker-compose
docker compose up -d
```
Then create a project at `http://localhost:3000` and copy your secret and public keys to `.env`.

## Running the Application

### ⚡ 1-Command All-In-One Startup (Recommended)
You can start all 3 services (Mock IT API, FastAPI Backend, and Streamlit UI) together with one single command:
```powershell
.\myvenv\Scripts\Activate.ps1
python run.py
```
*(Press `Ctrl+C` in that terminal anytime to stop all 3 services together).*

---

### Manual Multi-Terminal Startup
If you prefer running services in separate terminals:

**Terminal 1 (Mock API & Main Backend):**
```powershell
.\myvenv\Scripts\Activate.ps1
uvicorn mock_services.main:app --port 8001
```

**Terminal 2 (Main LangGraph API):**
```powershell
.\myvenv\Scripts\Activate.ps1
python app/main.py
```

**Terminal 3 (Streamlit UI):**
```powershell
.\myvenv\Scripts\Activate.ps1
streamlit run ui/app.py
```

