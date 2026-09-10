# Architecture

## Modular Monolith
The POC is structured as a Modular Monolith.
It is appropriate for POC scale, easy for local development and debugging, provides clear separation of concerns, and avoids distributed-system overhead.

## Components
- **api**: FastAPI application serving as the main entry point.
- **agents**: LLM wrappers with specific responsibilities (Triage, Knowledge, Action, Response).
- **graph**: LangGraph defining the AI workflow and state.
- **tools**: Tools that agents can use (Knowledge search, Access check, etc.).
- **mcp**: Model Context Protocol boundary for standardized tool execution (to be implemented).
- **guardrails**: Input, Output, and Tool security checks.
- **memory**: Local SQLite for long-term memory, LangGraph state for short-term.
- **prompts**: Externalized prompt management.
- **clients**: HTTP client for calling internal/mock services.
- **observability**: Structured logging and optional Langfuse tracing.
- **config**: Centralized configuration management using Pydantic.

