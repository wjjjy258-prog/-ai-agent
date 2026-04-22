# Aurora Agent (Web + Multi Provider)

This project is a local AI agent with:

- ChatGPT-style web interface
- Multi-conversation history
- Task/note tools (task create/list/complete, daily plan, weekly review)
- Ollama integration (default model: `qwen3.5:4b`)
- OpenAI-compatible API provider integration (DashScope/Bailian compatible)
- Streaming responses in web chat
- Model dropdown switcher from local Ollama model list
- SQLite persistence

## 1. Setup

Requires Python 3.10+.

```bash
cd /path/to/project
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e .
```

## 2. Run Web App

```bash
aurora-web
```

If script is not on PATH:

```bash
python -m ai_agent.web.app
```

Open: http://127.0.0.1:8000

One-click launcher on Windows (double-click supported):

```bash
start_aurora_web.bat
```

It automatically creates `.venv`, installs dependencies, applies default env vars,
checks model service reachability, auto-starts Ollama when needed (provider=ollama),
starts the server, and opens browser.

## 3. LLM Environment Variables

Default values:

- `AURORA_LLM_PROVIDER=ollama`
- `AURORA_OLLAMA_BASE_URL=http://127.0.0.1:11434`
- `AURORA_OLLAMA_MODEL=qwen3.5:4b`
- `AURORA_OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
- `AURORA_OPENAI_MODEL=qwen-plus`
- `AURORA_OPENAI_API_KEY=` (optional, can also be set in UI settings)

Optional:

- `AURORA_ENABLE_LLM_CHAT=true|false`
- `AURORA_OLLAMA_TIMEOUT_SEC=180`
- `AURORA_OPENAI_TIMEOUT_SEC=120`
- `AURORA_LLM_HISTORY_LIMIT=20`
- `AURORA_INTENT_CONFIDENCE_THRESHOLD=0.72`

## 4. Endpoints

- `GET /api/runtime` runtime info and model availability
- `GET /api/models` model list for dropdown
- `POST /api/conversations/{id}/messages` non-stream message
- `POST /api/conversations/{id}/messages/stream` stream message (NDJSON)

## 5. DashScope / Bailian Quick Setup

In UI Settings:

1. Set provider to `OpenAI compatible API`.
2. Set base URL to `https://dashscope.aliyuncs.com/compatible-mode/v1`.
3. Set your API key.
4. Set model (for example `qwen-plus`).

Then save settings and start chatting. Ollama is not required in this provider mode.

## 6. Run Tests

```bash
python -m unittest discover -s tests -v
```
