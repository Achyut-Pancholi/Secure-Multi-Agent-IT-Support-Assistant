# Architectural Decisions

## Why Modular Monolith?
**Context**: We need to build a multi-agent application with various components (API, DB, UI).
**Decision**: Use a Modular Monolith architecture.
**Reason**: It provides a clear separation of concerns (API, agents, graph, tools) without the complexity of managing distributed microservices. It's ideal for a POC scale.
**Trade-offs**: Scaling individual components independently is harder, but acceptable for a POC.

## Why LangGraph?
**Context**: Need to orchestrate multiple agents.
**Decision**: Use LangGraph.
**Reason**: Provides explicit state management and conditional routing, allowing us to build robust, cyclical workflows instead of relying solely on LLM chaining.
**Trade-offs**: Slightly steeper learning curve than simple LangChain chains.

## Why Groq & OpenAI OSS Models?
**Context**: Need a performant open-source/open-weight LLM provider for the POC.
**Decision**: Use Groq hosting OpenAI OSS models (`openai/gpt-oss-120b` and `openai/gpt-oss-20b`).
**Reason**: OpenAI's open-weights models (`gpt-oss-120b` / `gpt-oss-20b`) combined with Groq's high-speed LPU inference offer state-of-the-art agentic performance, reasoning, and tool use with low latency and zero cost on Groq's free tier.
**Trade-offs**: Requires a Groq API key and network connection.

## Why Langfuse optional?
**Context**: Need observability for LLM calls.
**Decision**: Support Langfuse, but make it completely optional.
**Reason**: Provides excellent trace visualization, but we must ensure the core POC can run at zero cost and without requiring third-party SaaS accounts.
**Trade-offs**: If a user doesn't configure it, they rely only on standard Python logging.

