# POC2: Secure Multi-Agent IT Support Assistant
## Mentor Deep Dive Guide

> **Purpose:** A concept-by-concept walkthrough of every major engineering decision in this project.
> Each concept is explained with **What / Why / How / Where**.

---

## Table of Contents

| # | Concept | Key Files |
|---|---|---|
| 1 | Multi-Agent Architecture & LangGraph | `app/graph/workflow.py`, `app/graph/state.py` |
| 2 | Security Guardrails — Three Layers | `app/guardrails/` |
| 3 | Memory Management — Short & Long Term | `app/memory/long_term.py` |
| 4 | Prompt Management — Langfuse + Fallback | `app/prompts/manager.py` |
| 5 | Tool Use & ReAct Pattern | `app/agents/`, `app/tools/` |
| 6 | RAG — Retrieval-Augmented Generation | `app/tools/knowledge.py` |
| 7 | Structured Outputs & Pydantic | `app/models.py` |
| 8 | API Design — REST, SSE & WebSocket | `app/api/routes.py` |
| 9 | AI Observability with Langfuse | `app/observability/logging.py` |
| 10 | Mock API & HTTP Client Resilience | `mock_services/main.py` |
| 11 | Environment-Based Configuration | `app/config.py` |
| 12 | End-to-End Request Lifecycle | Full trace |
| 13 | Testing Strategy | `tests/` |
| 14 | Key Takeaways | — |

---

## 1. Multi-Agent Architecture & LangGraph Orchestration

### WHAT
A **multi-agent system** splits work between specialized AI agents that collaborate through a shared state.
Four agents are connected inside a **LangGraph stateful workflow graph**:

| Agent | Role | Tools it owns |
|---|---|---|
| `TriageAgent` | Classifies request and decides routing | None — pure LLM reasoning |
| `KnowledgeAgent` | Searches internal KB articles via RAG | `search_knowledge_base` |
| `ActionAgent` | Calls internal IT APIs for real actions | `check_user_access`, `check_service_status`, `create_support_ticket` |
| `ResponseAgent` | Synthesizes the final user-facing answer | None — pure LLM synthesis |

**LangGraph** connects these as a directed graph. Nodes are agents or guardrails. Edges can be
**conditional** — the graph takes a different path based on runtime state.

### WHY
A "one big agent with all tools" approach fails because:
1. **Security:** You cannot prevent an agent role from using another's tools at the prompt level alone.
2. **Debuggability:** When something fails, you know which node failed — not "somewhere in the LLM."
3. **Maintainability:** Swapping the KB search strategy only touches `KnowledgeAgent`.

### HOW

**`app/graph/state.py` — Shared state (communication protocol between all nodes)**
```python
class SupportState(TypedDict):
    request_id: str
    user_id:    str
    user_query: str
    history:    Optional[List[Dict[str, str]]]  # conversation turns

    category:  Optional[str]        # set by Triage
    priority:  Optional[Priority]   # Enum: LOW/MEDIUM/HIGH
    route:     Optional[Route]      # KEY FIELD: KNOWLEDGE/ACTION/UNKNOWN

    agent_outputs:  List[str]       # accumulated findings from specialist agents
    final_response: Optional[str]   # set by ResponseAgent
    errors:         List[str]       # guardrail failures propagate here
```
Every node returns only the keys it changed. LangGraph merges the partial update automatically.

**`app/graph/workflow.py` — The graph definition**
```python
workflow = StateGraph(SupportState)

workflow.add_node("input_guardrail",  node_input_guardrail)
workflow.add_node("triage_agent",     node_triage)
workflow.add_node("knowledge_agent",  node_knowledge)
workflow.add_node("action_agent",     node_action)
workflow.add_node("response_agent",   node_response)
workflow.add_node("output_guardrail", node_output_guardrail)

workflow.set_entry_point("input_guardrail")
workflow.add_edge("input_guardrail", "triage_agent")

# Dynamic routing: the triage LLM decision controls the execution path
workflow.add_conditional_edges(
    "triage_agent",
    route_request,        # function returning the name of next node
    {
        "knowledge_agent": "knowledge_agent",
        "action_agent":    "action_agent",
        "response_agent":  "response_agent",
    }
)

workflow.add_edge("knowledge_agent", "response_agent")
workflow.add_edge("action_agent",    "response_agent")
workflow.add_edge("response_agent",  "output_guardrail")
workflow.add_edge("output_guardrail", END)

app = workflow.compile()   # validates graph, returns .invoke()/.stream() Runnable
```

`.compile()` validates no dead-end nodes exist, then returns a `Runnable` supporting `.invoke()` (synchronous)
and `.stream()` (node-by-node progress events).

### WHERE
- `app/graph/workflow.py`, `app/graph/state.py`, `app/agents/`

### Diagram
```
[Input Guardrail] -> [Triage Agent] --KNOWLEDGE--> [Knowledge Agent] --+
                           |                                            +--> [Response Agent] -> [Output Guardrail] -> END
                           +--ACTION-->  [Action Agent]  --------------+
                           +--UNKNOWN-> [Response Agent] --------------+
```

---

## 2. Security Guardrails — Three Defense Layers

### WHAT
Guardrails are **deterministic, code-level checks** at specific positions in the workflow that catch
security violations independently of any LLM behavior. Three layers, three threat surfaces:

| Layer | Position | Threat caught |
|---|---|---|
| **Input Guardrail** | First node, before any LLM | Prompt injection, empty input, oversized queries |
| **Tool RBAC Guardrail** | Inside every tool wrapper | Unauthorized agent-to-tool access |
| **Output Guardrail** | Last node, before user sees response | Leaked secrets, internal IPs |

### WHY
**Defense-in-depth:** Each layer guards a different part of the attack surface.
If one layer is bypassed, the others still protect.

> Core principle: "Prompts are not security. Code is security."
> A prompt says *please don't do this*. Code says *you cannot do this*.

### HOW — Layer 1: Input Guardrail (`app/guardrails/input.py`)
```python
def validate_input(query: str, user_id: str) -> str:
    if not query.strip():     raise ValueError("Empty query.")
    if not user_id:           raise ValueError("User identity required.")
    if len(query) > 1000:     raise ValueError("Query too long.")

    for phrase in ["ignore previous instructions", "system prompt", "bypass security"]:
        if phrase in query.lower():
            raise ValueError("Input rejected (INP-SEC-01).")
    return query.strip()
```
On failure: `state["errors"]` is populated. All downstream nodes skip with `if state.get("errors"): return state`.
The entire LLM workflow is **bypassed** and ResponseAgent outputs a safe error message.

### HOW — Layer 2: Tool RBAC Guardrail (`app/guardrails/tool.py`)
```python
TOOL_POLICY = {
    "knowledge_agent": ["search_knowledge_base"],
    "action_agent":    ["check_user_access", "check_service_status", "create_support_ticket"],
    "triage_agent":    [],
    "response_agent":  [],
}

def authorize_tool_call(agent_name: str, tool_name: str):
    if tool_name not in TOOL_POLICY.get(agent_name, []):
        raise AuthorizationError(f"Agent '{agent_name}' cannot use '{tool_name}'")
```
Every tool wrapper calls this before executing. Even if a KnowledgeAgent LLM were manipulated
into wanting to call `create_support_ticket`, it receives `AuthorizationError` — unbypassable at code level.

### HOW — Layer 3: Output Guardrail (`app/guardrails/output.py`)
```python
def validate_output(response: str) -> str:
    if "mock-internal-token-secret" in response:
        return "Response blocked: Safety violation (OUT-SEC-01)."

    if re.search(r'(10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)', response):
        return "Response blocked: Internal infrastructure details cannot be disclosed."

    return response
```

### WHERE
- `app/guardrails/input.py`, `app/guardrails/tool.py`, `app/guardrails/output.py`
- Applied in graph: `app/graph/workflow.py`

---

## 3. Memory Management — Short-Term & Long-Term

### WHAT
AI systems are **stateless by default**. This project implements two memory layers:

| Type | Stores | Lifetime | Backend |
|---|---|---|---|
| **Short-term** | Last 4 conversation turns | Single session | `SupportState.history` in-memory |
| **Long-term** | User attributes across sessions | Permanent | SQLite file |

### WHY
- **Short-term:** Enables follow-up handling. When user replies "yes" to "shall I open a ticket?",
  the TriageAgent needs prior context to understand what "yes" means.
- **Long-term:** Enables continuity and personalization across sessions.
- **Why separate?** Short-term must be fast (in-memory), long-term must be durable (disk).
  Conflating them leads to wrong design trade-offs.

### HOW — Short-Term Memory
**`app/graph/workflow.py` — `build_conversation_context()`**
```python
def build_conversation_context(state: SupportState) -> str:
    history = state.get("history") or []
    if not history:
        return state["user_query"]
    # Last 4 messages keeps context window manageable
    lines = [f"{m['role'].capitalize()}: {m['content']}" for m in history[-4:]]
    return f"Previous Conversation:\n{chr(10).join(lines)}\n\nLatest: {state['user_query']}"
```
This context string is injected into Triage and Action agents so they reason over the full conversation.

### HOW — Long-Term Memory (`app/memory/long_term.py`)
```sql
CREATE TABLE user_memory (
    user_id    TEXT PRIMARY KEY,
    attributes TEXT   -- JSON: {"preferred_contact": "email", "known_issues": ["vpn"]}
)
```
```python
get_user_memory(user_id)            # load user profile
save_user_memory(user_id, attrs)    # overwrite
update_user_memory(user_id, new)    # merge (non-destructive)
```
**Why JSON blob?** Different users have different attributes. JSON avoids schema migration pain.
**Why SQLite?** Zero setup. The interface stays stable — replace with PostgreSQL/DynamoDB tomorrow
without changing any callers. This is **design for replaceability**.

### WHERE
- Short-term: `app/graph/state.py` (history field) + `app/graph/workflow.py` (build_conversation_context)
- Long-term: `app/memory/long_term.py`

---

## 4. Prompt Management — Langfuse + Local Fallback

### WHAT
Prompt Management treats prompts as **versioned, deployable artifacts** — not hardcoded strings.
The `PromptProvider` class:
1. **First** tries to load a prompt from Langfuse (remote versioned prompt store)
2. **Falls back** to locally-defined prompts when Langfuse is unavailable

### WHY
Without prompt management: changing a prompt requires code edit -> commit -> redeploy. Slow, and mixes
config with code.

With Langfuse prompt management: edit in the Langfuse UI -> click "Deploy" -> the live service picks it
up on the next request. **Zero redeploy.** The local fallback means the system works in development
without any Langfuse account.

### HOW
**`app/prompts/manager.py`**
```python
class PromptProvider:
    def get_prompt(self, prompt_name: str) -> ChatPromptTemplate:
        # Step 1: Try Langfuse (live, versioned)
        if self.langfuse_client:
            try:
                lf_prompt = self.langfuse_client.get_prompt(prompt_name)
                logger.info(f"Loaded '{prompt_name}' from Langfuse v{lf_prompt.version}")
                return ChatPromptTemplate.from_messages([("system", lf_prompt.prompt)])
            except Exception:
                pass   # graceful degradation to local

        # Step 2: Local fallback
        template = LOCAL_PROMPTS.get(prompt_name)
        return ChatPromptTemplate.from_messages([("system", template)])
```

**Each agent has a dedicated prompt with strict grounding rules:**
- **Triage:** Classify intent, route to KNOWLEDGE or ACTION, output exact JSON schema.
- **Knowledge:** STRICTLY answer only from KB tool results. Forbidden from hallucinating general IT advice.
- **Action:** Tool selection guide. Special handling for confirmation replies ("yes", "go ahead").
- **Response:** Synthesize findings into user-friendly language. Forbidden from including raw IPs or tokens.

### WHERE
- `app/prompts/manager.py`
- Consumed by: `app/agents/triage.py`, `app/agents/knowledge.py`, `app/agents/action.py`, `app/agents/response.py`

---

## 5. Tool Use & ReAct Agent Pattern

### WHAT
A **tool** is a Python function that the LLM can call during its reasoning loop.
**ReAct** (Reasoning + Acting) is the iterative pattern:
Think -> Act (call a tool) -> Observe result -> Think again, until enough info to answer.

### WHY
LLMs cannot access real-time data (live access rights, current service status).
Tools provide **deterministic, real-world-grounded data** from actual APIs — not stale training memory.

### HOW — Defining a Tool
**`app/tools/knowledge.py`**
```python
@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the internal IT support knowledge base for official troubleshooting articles.
    Provide a specific query to find relevant articles.
    """
    # ChromaDB vector similarity search
```
The `@tool` decorator reads the docstring and sends it to the LLM as the tool description.
**Good docstrings = better tool selection accuracy.**

### HOW — ReAct Loop
**`app/agents/knowledge.py`**
```python
agent = create_react_agent(model=self.llm, tools=self.tools, prompt=system_instruction)
result = agent.invoke({"messages": [HumanMessage(content=query)]})
```

The loop runs automatically:
```
Thought:     User asked about VPN. I should search the knowledge base.
Action:      search_knowledge_base("VPN connectivity issues")
Observation: [{"content": "KB001: VPN Troubleshooting Steps...", "score": 0.43}]
Thought:     Found a relevant article. I can now answer.
Final Answer: Based on KB001, here are the troubleshooting steps...
```

### HOW — Tool Authorization Wrapping
**`app/agents/action.py`**
```python
def authorized_check_user_access(user_id: str) -> str:
    authorize_tool_call("action_agent", "check_user_access")  # Layer 2 guardrail
    return check_user_access.invoke({"user_id": user_id})

auth_tool = StructuredTool.from_function(
    func=authorized_check_user_access,
    name="check_user_access",
    description="Check the current access permissions for a specific user."
)
```
`StructuredTool.from_function` wraps the authorization-gated function with proper LangChain metadata.

### WHERE
- Tools: `app/tools/`
- Agent implementations: `app/agents/knowledge.py`, `app/agents/action.py`

---

## 6. RAG — Retrieval-Augmented Generation

### WHAT
Instead of asking the LLM to answer from training memory (outdated, hallucinated), RAG:
1. **Retrieves** relevant documents from a trusted source
2. **Augments** the LLM prompt with those documents
3. **Generates** an answer grounded only in retrieved content

### WHY
Without RAG: LLM answers "How do I fix VPN?" from generic internet training data — generic and outdated.
With RAG: LLM answers from your **actual internal KB article** — company-specific, current, auditable.

### HOW — 5-Step Pipeline (`app/tools/knowledge.py`)

**Step 1 — Source data** (`data/knowledge/kb.json`):
```json
[{"id": "KB001", "title": "VPN Connectivity Issues", "content": "...", "tags": ["vpn"]}]
```

**Step 2 — Embedding** (convert text to semantic vectors):
```python
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# ~384-dimensional float vector representing the meaning of text
```

**Step 3 — Storage** (ChromaDB — local file-based vector database):
```python
vector_store = Chroma.from_texts(
    texts=texts, embedding=embeddings, persist_directory=CHROMA_DB_PATH
)
```

**Step 4 — Query-time retrieval**:
```python
results_with_score = vector_store.similarity_search_with_score(query, k=2)
# Returns top-2 most semantically similar articles + their distance scores
```

**Step 5 — Relevance threshold (CRITICAL)**:
```python
THRESHOLD = 1.15   # ChromaDB L2 distance; lower = more similar

for doc, score in results_with_score:
    if score < THRESHOLD:
        relevant_results.append(doc)   # only genuinely relevant results pass

if not relevant_results:
    return "NO_RELEVANT_ARTICLES_FOUND: No approved article exists for this issue."
```

**Why the threshold matters:** Without it, the agent always returns the "least bad" match —
even for completely unrelated questions. The threshold enforces honest **"I don't know"** behavior
and prevents hallucination on irrelevant context.

### WHERE
- Full pipeline: `app/tools/knowledge.py`
- KB data: `data/knowledge/kb.json`
- Vector DB: `data/knowledge/chroma_db/` (git-ignored, rebuilt on startup if missing)

---

## 7. Structured Outputs & Pydantic Contracts

### WHAT
**Structured output** forces the LLM to return data as a specific JSON schema, validated and parsed
as a Pydantic model. Instead of parsing free-form text, you get a guaranteed typed object.

### WHY
The Triage Agent routing decision must be machine-readable: `if route == Route.KNOWLEDGE: ...`.
If the LLM returns "I think this is a knowledge question", there is no reliable extraction.
Structured output guarantees a `TriageResult` object with validated, type-safe fields.

### HOW
**`app/models.py`**
```python
class Route(str, Enum):
    KNOWLEDGE = "KNOWLEDGE"   # rejects "knowledge", "Knowledge", "kb", etc.
    ACTION    = "ACTION"
    UNKNOWN   = "UNKNOWN"

class TriageResult(BaseModel):
    category: str        # e.g., "connectivity", "access"
    priority: Priority   # Enum-validated
    route:    Route      # Enum-validated — drives conditional routing
    reason:   str        # human-readable explanation for auditing
```

**`app/agents/triage.py`**
```python
structured_llm = self.llm.with_structured_output(TriageResult)
chain = prompt | structured_llm
result = chain.invoke({"query": query})
# result is a guaranteed TriageResult — .route is always KNOWLEDGE/ACTION/UNKNOWN
```

LangChain converts `TriageResult` to a JSON schema, sends it to the Groq API as a response format
constraint. The LLM must produce matching JSON. Pydantic validates and parses it.

**Why Enums?** Without enums, LLM inconsistency breaks routing: "knowledge" != "KNOWLEDGE".
Pydantic Enums reject anything outside the allowed set with a `ValidationError` immediately.

**Pydantic also used for:**
- FastAPI request/response validation — auto-rejects malformed JSON with 422 errors
- Internal data contracts: `SupportRequest`, `SupportResponse`, `ErrorResponse`

### WHERE
- `app/models.py`, `app/agents/triage.py`, `app/api/schemas.py`

---

## 8. API Design — REST, SSE & WebSocket

### WHAT
Three communication patterns exposed via FastAPI, each suited to different client needs:

| Endpoint | Protocol | Direction | Use case |
|---|---|---|---|
| `POST /api/v1/support` | HTTP REST | Request -> Response | Streamlit UI — blocks until complete |
| `POST /api/v1/support/stream` | HTTP + SSE | Server -> Client | Live node-completion progress events |
| `WS /ws/runs/{id}` | WebSocket | Bidirectional | Real-time interactive clients |

### WHY Three Patterns?
- **REST** is simple but blocks the client for ~4 seconds during LLM processing.
- **SSE** streams progress events ("Triage complete... KB search running...") as each LangGraph
  node finishes. One-directional only — simple to implement, no library needed on client.
- **WebSocket** is bidirectional — enables future mid-workflow user input (clarification questions,
  live typing). More complex, architecturally complete.

### HOW — SSE Streaming
**`app/api/routes.py`**
```python
@router.post("/support/stream")
async def stream_support_request(request: SupportRequestSchema):
    async def event_generator():
        for step_event in app_workflow.stream(initial_state):
            node_name = list(step_event.keys())[0]
            yield f"data: {json.dumps({'event': f'{node_name}_completed'})}\n\n"

            if node_name == "output_guardrail":
                final_resp = step_event[node_name].get("final_response", "")
                yield f"data: {json.dumps({'event': 'completed', 'response': final_resp})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```
SSE format: `data: <json>\n\n` — double newline signals end of one event.
Browser `EventSource` API reads these natively without any library.

### HOW — WebSocket
```python
@router.websocket("/ws/runs/{request_id}")
async def websocket_endpoint(websocket: WebSocket, request_id: str):
    await websocket.accept()
    data = await websocket.receive_text()      # client sends query via WebSocket
    payload = json.loads(data)

    # LangGraph .stream() is synchronous — run in thread pool to avoid blocking async event loop
    steps = await asyncio.to_thread(lambda: list(app_workflow.stream(initial_state)))

    for step_event in steps:
        node_name = list(step_event.keys())[0]
        await websocket.send_json({"event": f"{node_name}_completed"})
```
**`asyncio.to_thread()`:** LangGraph's synchronous `.stream()` would block the async FastAPI event loop
if called directly. `to_thread()` offloads it to a thread pool, keeping FastAPI responsive.

### HOW — API Security
```python
async def verify_app_token(authorization: str = Header(...)):
    token = authorization.replace("Bearer ", "")
    if token != settings.app_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
```
Applied as FastAPI `Depends` on all REST endpoints.

### WHERE
- `app/api/routes.py`, `app/api/auth.py`, `app/main.py`

---

## 9. AI Observability with Langfuse

### WHAT
**AI Observability** = recording every LLM call (exact prompt, output, latency, token count, user ID,
session context) for debugging, monitoring, and improvement. Langfuse provides the dashboard.

### WHY
Standard logging tells you *that* a call happened. Langfuse tells you:
- The **exact prompt** the LLM received (including injected KB articles)
- The **exact LLM output** before guardrails processed it
- **Latency per agent** — which node is causing slowdowns?
- **Per-user analytics** — which users see the most errors?
- **Session grouping** — all turns in one conversation are linked together

Without Langfuse, debugging a wrong answer means guessing. With Langfuse, you replay the exact trace.

### HOW
**`app/observability/logging.py`**
```python
def get_langfuse_callback(user_id, session_id, trace_name, metadata):
    if settings.is_langfuse_enabled():
        trace_context = TraceContext(
            user_id=user_id,          # per-user grouping in dashboard
            session_id=session_id,    # per-request grouping
            trace_name=trace_name,
            tags=["it-support-assistant", settings.app_env],
            metadata={"model": settings.groq_model}
        )
        return CallbackHandler(public_key=..., trace_context=trace_context)
    return None   # graceful degradation — no crash, no error
```

The callback propagates through the entire call chain:
```python
config = {"callbacks": [langfuse_cb]} if langfuse_cb else {}
final_state = app_workflow.invoke(initial_state, config=config)
# LangGraph passes config -> each agent -> each LLM call -> Langfuse captures everything
```

**Graceful degradation:** When Langfuse is not configured, `return None` — system works identically.
The monitoring layer **must never crash the application it monitors**.

**Flushing (critical for data integrity):**
```python
def flush_langfuse(handler):
    handler.flush()   # called in every finally block
```
Langfuse batches traces asynchronously. Without explicit `flush()`, traces are lost when
the server process terminates between requests.

### WHERE
- `app/observability/logging.py`
- Applied in: `app/api/routes.py` (every endpoint)

---

## 10. Mock Internal API & HTTP Client Resilience

### WHAT
**Mock Internal API:** A real FastAPI server simulating enterprise IT systems (user directory,
service monitor, ticketing system) that would exist in a real company.

**HTTP Client Resilience:** `InternalAPIClient` built with production-grade error handling.

### WHY a Real Mock (Not Just Mocked Functions)?
By building a real HTTP server, `ActionAgent` makes **actual HTTP calls** — real headers, JSON
serialization, auth, timeouts, and error codes. This exercises the full integration path including
all resilience logic that would be invisible with function-level mocks.

### HOW — Mock API (`mock_services/main.py`)
```python
mock_users = {
    "user123": {"vpn_access": True,  "finance_access": False},   # Engineering
    "user456": {"vpn_access": True,  "finance_access": True},    # Finance dept
}
mock_services = {
    "vpn":        {"status": "degraded",    "active_incidents": 1},   # VPN incident for demo
    "finance_db": {"status": "operational", "active_incidents": 0},
}
# All endpoints: Authorization: Bearer mock-internal-token-secret
```

### HOW — Four Resilience Patterns (`app/clients/internal_api.py`)

**1. Hard timeouts — prevents indefinite hangs:**
```python
self.timeout = 5.0
with httpx.Client(timeout=self.timeout) as client: ...
```

**2. Bounded retries with linear backoff:**
```python
while retries <= self.max_retries:   # max 3 total attempts
    try: response = client.request(...)
    except httpx.RequestError:
        retries += 1; time.sleep(1)  # 1-second pause
```

**3. No retry on POST timeout — prevents duplicate ticket creation:**
```python
if method.upper() == "POST":
    raise InternalAPIError("Ticket creation status unknown.")
# GET timeout -> safe to retry (server state unchanged)
# POST timeout -> server may or may not have processed it -> retrying = duplicate risk
```

**4. No retry on 4xx errors — unfixable by retrying:**
```python
if 400 <= status_code < 500:
    raise InternalAPIError(f"Client error: {status_code}")
# 404 = user not found. 403 = unauthorized. These won't change on retry.
```

### WHERE
- `mock_services/main.py`, `app/clients/internal_api.py`
- Tools: `app/tools/access.py`, `app/tools/service.py`, `app/tools/ticket.py`

---

## 11. Environment-Based Configuration

### WHAT
All configurable values (API keys, URLs, model names, feature flags) live in a single `Settings` class
backed by `.env`. Nothing hardcoded in source code.

### WHY
- **Security:** API keys never appear in git history.
- **Portability:** Dev -> staging -> production by changing only `.env`, zero code changes.
- **Discovery:** `.env.example` (committed, without real values) documents every required variable.

### HOW
**`app/config.py`**
```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    groq_api_key:     str           = ""
    groq_model:       str           = "openai/gpt-oss-120b"
    internal_api_url: str           = "http://localhost:8001"
    log_level:        str           = "INFO"

    langfuse_public_key: Optional[str] = None   # Langfuse disabled when absent
    langfuse_secret_key: Optional[str] = None

    def is_langfuse_enabled(self) -> bool:
        return bool(self.langfuse_public_key and self.langfuse_secret_key)

settings = Settings()   # singleton — all modules: from app.config import settings
```

One `Settings` object for the entire process. No module ever hardcodes a value.

### WHERE
- `app/config.py`, `.env.example`

---

## 12. End-to-End Request Lifecycle

**Scenario:** User `user123` sends: "My VPN is broken"

```
INCOMING REQUEST:
  POST /api/v1/support
  Body: {"user_id": "user123", "query": "My VPN is broken"}
  Header: Authorization: Bearer <app_token>

STEP 1  FastAPI: verify_app_token()  PASS

STEP 2  workflow.invoke(initial_state) starts

STEP 3  [input_guardrail] node
        - Not empty, user_id present, no injection phrases  ->  PASS
        - State update: {user_query: "My VPN is broken"}

STEP 4  [triage_agent] node
        - LLM call with with_structured_output(TriageResult)
        - category="connectivity", priority=HIGH, route=KNOWLEDGE
        - State update: {route: Route.KNOWLEDGE, priority: Priority.HIGH}

STEP 5  Conditional edge: route_request()
        - state["route"] == KNOWLEDGE  ->  next node = "knowledge_agent"

STEP 6  [knowledge_agent] node  --  ReAct loop
        Thought:     User asked about VPN. I should search the knowledge base.
        Action:      search_knowledge_base("VPN connectivity issues")
          - authorize_tool_call("knowledge_agent", "search_knowledge_base")  PASS
          - ChromaDB search  ->  KB001 found (score=0.43, threshold=1.15)  RELEVANT
        Observation: KB001 content returned
        Thought:     Article found. I can answer.
        Final:       "Steps from KB001: 1. Check VPN client version..."
        - State update: {agent_outputs: ["Knowledge Agent: Steps from KB001..."]}

STEP 7  [response_agent] node
        - LLM synthesizes agent_outputs + conversation history
        - State update: {final_response: "I found a KB article. Here are the steps..."}

STEP 8  [output_guardrail] node
        - No leaked token  PASS
        - No internal IP   PASS
        - State update: {final_response: (unchanged)}

STEP 9  END
        FastAPI returns: {"request_id": "uuid-xxx", "response": "I found...", "status": "completed"}

Total time: ~2-4 seconds (LLM calls dominate)
```

---

## 13. Testing Strategy

### WHAT & WHY
Tests focus on the **guardrail layer** because guardrail bugs are security failures, not just wrong answers.

**`tests/test_guardrails.py`**
```python
def test_prompt_injection_blocked():
    with pytest.raises(ValueError):
        validate_input("ignore previous instructions", "user1")

def test_empty_query_blocked():
    with pytest.raises(ValueError):
        validate_input("", "user1")

def test_output_secret_leakage_blocked():
    result = validate_output("The token is mock-internal-token-secret")
    assert "blocked" in result.lower()

def test_output_ip_leakage_blocked():
    result = validate_output("Connect to server 192.168.1.100")
    assert "blocked" in result.lower()
```

**Running:**
```powershell
.\myvenv\Scripts\Activate.ps1
pytest tests/ -v
```

### WHERE
- `tests/test_guardrails.py`, `tests/test_scenarios.py`, `tests/conftest.py`

---

## 14. Key Takeaways & What I Learned

1. **State is the nervous system of multi-agent workflows.**
   `SupportState` is the communication protocol between agents. Designing it well — what fields to include,
   their types, how errors propagate — determines how cleanly agents collaborate.

2. **Guardrails must be layered and code-enforced.**
   Three independent layers at different positions. Code-level enforcement (throwing exceptions) cannot be
   bypassed by any prompt manipulation. "Prompts are not security."

3. **Structured outputs bridge probabilistic LLMs and deterministic code.**
   `with_structured_output(TriageResult)` makes LLM classification reliable enough to drive code branching.
   Without it, the entire routing system is fragile string parsing.

4. **RAG quality = embedding model + relevance threshold.**
   The threshold (1.15) is the most critical tuning parameter — it enforces honest "I don't know" behavior
   and prevents hallucination on irrelevant context.

5. **Memory has two very different requirements.**
   Short-term (fast, ephemeral, in-state dict) vs long-term (durable, SQLite). Conflating them leads to
   wrong design trade-offs. Design each layer for its actual requirement.

6. **Prompt management is a deployment concern, not a code concern.**
   Centralizing in Langfuse lets non-engineers improve agent behavior without code changes or redeploys.
   The local fallback makes development frictionless.

7. **SSE and WebSocket solve different problems.**
   SSE = simple, server-only, progress events. WebSocket = bidirectional, interactive sessions.
   Choose the simplest that meets requirements.

8. **HTTP resilience patterns prevent production incidents.**
   Timeouts prevent hangs. Bounded retries prevent infinite loops. No-POST-retry prevents duplicate side effects.
   No-4xx-retry prevents wasted attempts. Each pattern addresses a real failure mode.

9. **Observability must degrade gracefully.**
   `return None` when Langfuse is not configured — system works identically.
   A monitoring component that can crash the monitored application is worse than no monitoring.

10. **Interface design enables replaceability.**
    `get_user_memory()` / `save_user_memory()` works for SQLite today, PostgreSQL tomorrow.
    Design to interfaces, not implementations.

---

*GitHub: https://github.com/Achyut-Pancholi/Secure-Multi-Agent-IT-Support-Assistant*
*Prepared for mentor review — POC2: Secure Multi-Agent IT Support Assistant*
