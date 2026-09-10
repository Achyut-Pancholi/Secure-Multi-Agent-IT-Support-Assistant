# Changelog / Development History

## 2026-09-10

### Added
- Added project directory structure.
- Added requirements.txt and `.env` configuration.
- Added app configuration and basic structured logging setup (Iteration 1).
- Added initial documentation (README.md, CHANGES.md, architecture.md, decisions.md, ai_workflow.md).
- Added persistent Chroma DB knowledge base using local HuggingFace embeddings.
- Added interactive Mermaid AI workflow diagram in docs/ai_workflow.md.
- Configured Groq to use OpenAI OSS models (`openai/gpt-oss-120b` / `openai/gpt-oss-20b`).
- Added documentation for local Langfuse deployment via Docker Compose.
- Added `scripts/generate_diagram.py` and generated high-resolution PNG diagram `docs/ai_workflow.png`.
- Installed the official Langfuse AI Skill from `github.com/langfuse/skills` into `.agents/skills/langfuse/`.
- Instrumented the LangGraph workflow, SSE streaming, and WebSocket endpoints with unified Langfuse tracing following best practices (`user_id`, `session_id`, `trace_name`, tags, metadata, and automatic flushing).
- Integrated Langfuse Prompt Management in `app/prompts/manager.py` with seamless local fallbacks.
- Added strict zero-hallucination grounding prompt constraints and Chroma distance thresholding in `app/tools/knowledge.py`.
