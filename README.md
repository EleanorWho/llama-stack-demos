# Llama Stack Demos

A collection of hands-on demos for [Llama Stack](https://llamastack.io), covering everything from basic chat completions to RAG, agents, observability, and end-to-end applications. All demos run locally in your terminal.

## Quick Start

### Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- [Ollama](https://ollama.com/) (for local model serving)

### 1. Install dependencies

```bash
uv sync
```

### 2. Set up a model backend

These demos use [Ollama](https://ollama.com/) as the default model backend, but Llama Stack supports many others (vLLM, Together, Fireworks, OpenAI, etc.). See the [Llama Stack documentation](https://github.com/ogx-ai/ogx) for the full list of supported providers.

```bash
# Install Ollama from https://ollama.com/download, then:
ollama pull llama3.2:3b
```

### 3. Start a local Llama Stack server

Start the server in a separate terminal:

```bash
uvx --from 'llama-stack[starter]' llama stack run starter
```

The server listens on `localhost:8321` by default.

### 4. Run a demo

```bash
# Example: basic client setup
uv run python -m demos.01_foundations.01_client_setup localhost 8321
```

## Available Demos

All demos live under the `demos/` directory and can be run directly from the terminal.

| Directory | Topic | Description |
|-----------|-------|-------------|
| `01_foundations` | Foundations | Client setup, chat completions, vector DBs, tool registration, MCP |
| `02_responses_basics` | Responses API | Higher-level response generation with tools and structured outputs |
| `03_rag` | RAG | Retrieval-augmented generation with vector stores and search |
| `04_agents` | Agents | Conversational agents with chat, tools, RAG, and multi-agent coordination |
| `05_observability` | Observability | OpenTelemetry, Jaeger, Prometheus, and Grafana integration |
| `06_openai_compatibility` | OpenAI Compatibility | Using OpenAI-compatible endpoints with Llama Stack |
| `07-end-to-end-apps` | End-to-End Apps | Full applications (e.g. Knowledge Assistant) |


Each demo directory has its own README with detailed instructions and learning objectives. Start with `01_foundations` if you are new to Llama Stack.

## Optional: Kubernetes Deployment

If you want to deploy Llama Stack on Kubernetes instead of running locally, see [`deployment/kubernetes/`](deployment/kubernetes/) for manifests and instructions covering vLLM, the Llama Stack Kubernetes operator, and MCP servers on a Kind cluster.

## Resources

- [Llama Stack Documentation](https://ogx-ai.github.io/docs)
- [Llama Stack GitHub](https://github.com/ogx-ai/ogx)
- [Demo Structure & Design](DEMOS_STRUCTURE.md)
