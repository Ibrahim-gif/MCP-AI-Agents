# MCP + OpenTelemetry Tracing (OpenAI Agents + Azure OpenAI)

This repo runs an **OpenAI Agents** “task manager” agent that calls tools exposed by an **MCP server** (running over stdio), and emits **OpenTelemetry traces** that you can view locally in **VS Code AI Toolkit Tracing** via an OTLP collector endpoint.

---

## 1) What is an MCP server?

**MCP (Model Context Protocol)** is a standard way to connect LLM/agent runtimes to external capabilities (tools, data sources, services) through a consistent interface.

### Architecture (high level)

- **Agent runtime (client)**: your `client.py` code creates an Agent and runs it with `Runner.run(...)`.
- **MCP server(s)**: separate processes that expose **tools** (and sometimes resources/prompts) to the agent runtime.
- **Transport**: in your code you use **stdio transport** (`MCPServerStdio`) which means:
  - The MCP server runs as a subprocess (`uv run server.py`)
  - The client communicates with it via stdin/stdout messages
- **Tool calling loop**:
  1. Client asks server what tools exist (`list_tools`)
  2. Agent decides to call a tool
  3. Client sends tool invocation to server
  4. Server executes and returns structured results
  5. Agent continues reasoning with the results

### Why MCP is so useful for AI Agents

- **Decoupling**: tools live outside the agent process. You can update tools independently without changing agent logic.
- **Interoperability**: one agent runtime can connect to many MCP servers (calendar, email, ticketing, knowledge bases, etc.) using the same protocol.
- **Security boundaries**: credentials and privileged operations can be isolated inside the MCP server process.
- **Reusability**: the same MCP server can be shared across multiple agent projects and languages.
- **Observability**: tool calls are discrete, structured steps—great for tracing/debugging agent workflows end-to-end.

---

## 2) Project overview

- `client.py`  
  - Starts an MCP server via `MCPServerStdio` (subprocess: `uv run server.py`)
  - Creates an Agent with Azure OpenAI (`AsyncAzureOpenAI`)
  - Instruments OpenAI Agents + OpenAI calls using Logfire + OpenTelemetry
  - Exports traces (OTLP) to a local collector endpoint

- `server.py`  
  - Your MCP server implementation (tools live here)

- `.env`  
  - Holds Azure OpenAI credentials / endpoint

---

## 3) Prerequisites

- Python 3.10+ (3.11+ recommended)
- `uv` installed
- Azure OpenAI deployment created (you reference deployment name `gpt-4.1`)
- VS Code + **AI Toolkit** extension (for local trace viewing) :contentReference[oaicite:0]{index=0}

---

## 4) Environment variables

Create a `.env` file in the project root:

```env
AZURE_OPENAI_API_KEY=your_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com
```
---

## 5) Run 
### a) Create a virtual environment
```
uv venv
```

### b) Activate it
```
.\.venv\Scripts\Activate.ps1
```

### c) Install dependencies
```
uv pip install -r requirements.txt
```

### d) Run
```
uv run .\client.py
```
