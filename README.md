# MatOpt

A full-stack AI chat application with multi-provider model support and rich document parsing. Built with a FastAPI backend and a React + Vite frontend.

## Features

- **Multi-provider chat** — Switch between ChatGPT, DeepSeek, Qwen, Kimi, Llama, Gemini, and Tencent Hunyuan from the UI
- **Streaming responses** — Real-time token streaming via Server-Sent Events
- **Document parsing** — Upload and chat with PDF, DOCX, PPTX, PPT, DOC, Jupyter notebooks, images (PNG/JPG/JPEG/HEIC), and source code files (R, Rmd, Python, C, C++, Java)
- **Math rendering** — LaTeX expressions rendered inline via KaTeX
- **Rich output** — Syntax-highlighted code, Mermaid diagrams, and interactive charts (Chart.js, Plotly)
- **Conversation history** — Sidebar with session management and new-chat support

## Tech Stack

| Layer | Stack |
| --- | --- |
| Backend | Python 3.11, FastAPI, Uvicorn, OpenAI SDK |
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
| `POST` | `/api/documents/parse` | Parse and extract text from an uploaded file |
