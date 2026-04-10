# MatOpt

A full-stack AI chat application with multi-provider model support and rich document parsing. Built with a FastAPI backend and a React + Vite frontend.

## Features

- **Multi-provider chat** — Switch between ChatGPT, DeepSeek, Qwen, Kimi, Llama, Gemini, and Tencent Hunyuan from the UI
- **Streaming responses** — Real-time token streaming via Server-Sent Events
- **Agentic graph generation** — LangChain + LangGraph backend flow that can produce structured visual artifacts
- **Visual artifacts** — First-class SVG and interactive HTML outputs rendered directly in chat
- **MCP-ready tools** — Local MCP server (`backend/mcp_server.py`) for graph scaffolding and skill management tools
- **Document parsing** — Upload and chat with PDF, DOCX, PPTX, PPT, DOC, Jupyter notebooks, images (PNG/JPG/JPEG/HEIC), and source code files (R, Rmd, Python, C, C++, Java)
- **Math rendering** — LaTeX expressions rendered inline via KaTeX
- **Rich output** — Syntax-highlighted code, Mermaid diagrams, and interactive charts (Chart.js, Plotly)
- **Conversation history** — Sidebar with session management and new-chat support
- **SKILL.md management** — Built-in CRUD APIs for agent skill documents under `backend/skills/`
- **Automatic skill routing** — Backend auto-detects relevant skills from user intent and injects them into agentic runs (no manual UI selection required)

## Tech Stack

| Layer | Stack |
| --- | --- |
| Backend | Python 3.11, FastAPI, Uvicorn, OpenAI SDK, LangChain, LangGraph, MCP |
| Frontend | React 19, TypeScript, Vite, react-markdown, KaTeX, Plotly |
| Document parsing | PyMuPDF, python-docx, python-pptx, Pillow, LibreOffice (optional) |

## Prerequisites

- Python 3.11+
- Node.js 18+
- An OpenAI-compatible API key

## Quick Start

```bash
# Clone the repo
git clone <repo-url>
cd matopt

# Add your API key
echo "OPENAI_API_KEY=sk-..." > backend/.env

# Start everything (installs deps automatically on first run)
./run.sh start
```

The app will be available at `http://localhost:5173`. The backend runs on `http://localhost:8000`.

## Environment Variables

Create `backend/.env`:

```env
OPENAI_API_KEY=sk-...          # Required
OPENAI_MODEL=gpt-4o-mini       # Optional, default: gpt-4o-mini
# OPENAI_API_KEY is reused by the agentic graph pipeline.
```

## Process Manager (`run.sh`)

`run.sh` manages the backend and frontend as background processes and handles dependency installation automatically.

```bash
./run.sh start      # Install deps and start backend + frontend
./run.sh stop       # Stop both services
./run.sh restart    # Restart both services
./run.sh status     # Show running status and URLs
./run.sh logs       # Follow live logs from both services
./run.sh audit      # Run npm audit on the frontend
./run.sh audit-fix  # Run npm audit fix on the frontend
```

Logs are written to `.runtime/logs/`.

## Supported File Types

| Category | Extensions |
| --- | --- |
| Documents | `.pdf`, `.doc`, `.docx`, `.ppt`, `.pptx` |
| Code / Notebooks | `.py`, `.ipynb`, `.r`, `.rmd`, `.c`, `.cpp`, `.java` |
| Images | `.png`, `.jpg`, `.jpeg`, `.heic` |

> **Note:** DOC/PPT parsing and first-page previews for DOCX/PPTX require [LibreOffice](https://www.libreoffice.org/) installed on the backend host.

## Manual Setup

If you prefer to run the services directly:

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000 --env-file .env
```

### Frontend

```bash
cd frontend
npm install
VITE_BACKEND_URL=http://localhost:8000 npm run dev
```

## API Endpoints

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/api/chat` | Non-streaming chat completion |
| `POST` | `/api/chat/stream` | Streaming chat via SSE |
| `GET` | `/api/skills` | List SKILL.md docs |
| `GET` | `/api/skills/{slug}` | Read one SKILL.md doc |
| `POST` | `/api/skills` | Create/update a SKILL.md doc |
| `DELETE` | `/api/skills/{slug}` | Delete a SKILL.md doc |
| `POST` | `/api/documents/parse` | Parse and extract text from an uploaded file |
