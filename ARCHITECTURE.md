# Architecture: Secure Enterprise RAG Agent (Internal Financial Analyst)

## Project Overview

A multi-tool AI financial analyst that uses Retrieval-Augmented Generation (RAG) to answer
questions from internal financial documents, enforces Role-Based Access Control (RBAC) so
interns cannot see confidential data, and orchestrates multiple tools (RAG, Calculator,
Web Search) through a LangGraph stateful agent.

---

## System Architecture

```
                         ┌─────────────────────────┐
                         │      User Query          │
                         └────────────┬────────────┘
                                      │
                         ┌────────────▼────────────┐
                         │   LangGraph Agent        │
                         │   (agent.py)             │
                         │                          │
                         │  ┌──────────────────┐    │
                         │  │  Planner Node     │    │
                         │  │  (Gemini LLM)     │    │
                         │  │  Decides which    │    │
                         │  │  tools to call    │    │
                         │  └────────┬─────────┘    │
                         │           │               │
                         │  ┌────────▼─────────┐    │
                         │  │ Tool Executor     │    │
                         │  │ Runs selected     │    │
                         │  │ tools in sequence │    │
                         │  └────────┬─────────┘    │
                         │           │               │
                         │  ┌────────▼─────────┐    │
                         │  │ Synthesizer Node  │    │
                         │  │ (Gemini LLM)      │    │
                         │  │ Combines outputs  │    │
                         │  │ into final answer │    │
                         │  └──────────────────┘    │
                         └──────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                   │
           ┌────────▼──────┐  ┌──────▼───────┐  ┌───────▼──────┐
           │  RAG Tool      │  │  Calculator  │  │  Web Search  │
           │  (LlamaIndex + │  │  (AST-based  │  │  (Tavily API)│
           │   ChromaDB)    │  │   safe eval) │  │              │
           │  + RBAC Filter │  │              │  │              │
           └────────────────┘  └──────────────┘  └──────────────┘
                    │
           ┌────────▼──────┐
           │   ChromaDB     │
           │  Vector Store  │
           │  (Local Disk)  │
           │  + Metadata    │
           │    Filtering   │
           └────────────────┘
```

---

## Tech Stack

| Layer              | Technology                       | Purpose                                    |
| :----------------- | :------------------------------- | :----------------------------------------- |
| **LLM**            | Google Gemini 2.0 Flash Lite     | Planning, synthesis, RAG Q&A               |
| **Embeddings**     | Gemini Embedding 001             | Vector embeddings for document chunks      |
| **RAG Framework**  | LlamaIndex                       | Document parsing, indexing, querying        |
| **Vector Database**| ChromaDB (local, persistent)     | Stores embeddings with metadata            |
| **Agent Framework**| LangGraph                        | Stateful graph-based agent orchestration   |
| **Web Search**     | Tavily API                       | Real-time financial data                   |
| **Calculator**     | Custom AST-based safe evaluator  | Financial math without `eval()` risk       |
| **Language**       | Python 3.9                       | Runtime                                    |
| **Environment**    | Virtual env (`tf-env-39/`)       | Dependency isolation                       |

---

## Week 1: Data Infrastructure (The Foundation)

### What Was Built

The entire data pipeline — from raw PDFs to a queryable vector database with RBAC metadata.

### Files Created

| File                  | Purpose                                                          |
| :-------------------- | :--------------------------------------------------------------- |
| `generate_samples.py` | Generates 6 sample PDF documents (3 public, 3 confidential)     |
| `ingest.py`           | Parses PDFs, assigns RBAC metadata, embeds and stores in ChromaDB|
| `query_test.py`       | Tests RBAC by querying as "intern" vs "admin" roles              |
| `peek_db.py`          | Utility to inspect ChromaDB contents (chunks, metadata)          |
| `list_models.py`      | Debug utility to list available Gemini models for the API key    |
| `requirements.txt`    | Python dependencies                                              |
| `.env`                | API keys (GOOGLE_API_KEY)                                        |

### Sample Documents

**Public (access_level: "all"):**
- `data/public/tesla_10k.pdf` — Tesla 2023 Form 10-K (Revenue: $96.8B)
- `data/public/apple_10k.pdf` — Apple 2023 Form 10-K (Revenue: $383.3B)
- `data/public/nvidia_10k.pdf` — NVIDIA 2023 Form 10-K (Revenue: $27.0B)

**Confidential (access_level: "admin"):**
- `data/confidential/q4_strategy.pdf` — Q4 strategy with "Project Phoenix" acquisition plan
- `data/confidential/ceo_memo.pdf` — CEO memo on hardware sales forecast
- `data/confidential/legal_update.pdf` — Pending litigation and $500M settlement

### Ingestion Pipeline (ingest.py)

```
PDFs (data/public/ + data/confidential/)
    │
    ▼
LlamaIndex SimpleDirectoryReader
    │   Parses PDFs into Document objects
    ▼
Metadata Assignment
    │   public docs  → access_level: "all"
    │   confidential → access_level: "admin"
    ▼
Gemini Embedding (gemini-embedding-001)
    │   Converts text chunks to vector embeddings
    ▼
ChromaDB (./chroma_db)
    │   Stores vectors + metadata on local disk
    ▼
VectorStoreIndex ready for queries
```

### RBAC Implementation

Access control is enforced at the **vector database query level**, not at the application level.
This means confidential documents are physically excluded from search results for unauthorized users.

- **Intern role:** Query includes `MetadataFilter(key="access_level", value="all")` — only public documents are returned.
- **Admin role:** No filter applied — all documents (public + confidential) are searchable.

### Rate Limit Handling

The Gemini free tier has strict rate limits. Both `ingest.py` and `query_test.py` implement:
- Small batch sizes (`insert_batch_size=10`) during ingestion
- Exponential backoff retry (`2^attempt * 5` seconds, max 60s) on `429 RESOURCE_EXHAUSTED` errors
- Delays between sequential queries (`time.sleep(10)`)

---

## Week 2: Agentic Logic (The Brain)

### What Was Built

A LangGraph-powered multi-tool agent that intelligently routes queries to the right tool(s),
executes them, and synthesizes a professional financial analysis response.

### Files Created

| File                       | Purpose                                                    |
| :------------------------- | :--------------------------------------------------------- |
| `agent.py`                 | Main LangGraph agent with Planner → Executor → Synthesizer|
| `tools/__init__.py`        | Package init for tools module                              |
| `tools/rag_tool.py`        | RAG search with RBAC metadata filtering                    |
| `tools/calculator_tool.py` | Safe math evaluator (AST-based, no `eval()`)               |
| `tools/web_search_tool.py` | Tavily API web search for real-time data                   |
| `test_agent.py`            | 3-scenario test: RAG, multi-tool, RBAC enforcement         |

### Agent Graph (agent.py)

The agent is a 3-node LangGraph `StateGraph`:

```
Entry → [Planner] → [Tool Executor] → [Synthesizer] → END
```

**State schema:**
```python
class AgentState(TypedDict):
    query: str          # User's question
    role: str           # "intern" or "admin"
    plan: str           # JSON plan from Planner (which tools to call)
    tool_outputs: dict  # Results from each tool
    final_answer: str   # Synthesized response
    iteration: int      # Loop counter
```

**Node 1 — Planner:**
- Receives the user query
- Calls Gemini with a system prompt listing available tools
- LLM returns a JSON plan specifying which tools to invoke and with what inputs
- Example output: `{"tools": [{"name": "RAG_SEARCH", "input": "Tesla revenue 2023"}]}`

**Node 2 — Tool Executor:**
- Parses the JSON plan
- Executes each tool sequentially with 2-second delays between calls
- Passes the user's `role` to the RAG tool for RBAC filtering
- Collects all outputs into a dict

**Node 3 — Synthesizer:**
- Receives the original query + all tool outputs
- Calls Gemini with a synthesis prompt
- Returns a professional financial analysis citing sources

### Tool Details

#### RAG Tool (tools/rag_tool.py)
- Connects to the ChromaDB created in Week 1
- Applies `MetadataFilter` based on user role (intern = public only, admin = all)
- Uses LlamaIndex `VectorStoreIndex.from_vector_store()` for semantic search
- Includes exponential backoff retry for rate limits

#### Calculator Tool (tools/calculator_tool.py)
- Uses Python's `ast` module to parse math expressions into an AST
- Only allows safe operations: `+`, `-`, `*`, `/`, `**`, `%`
- Supports functions: `abs`, `round`, `min`, `max`, `sum`, `sqrt`, `log`, `log10`
- Never calls `eval()` — prevents code injection attacks

#### Web Search Tool (tools/web_search_tool.py)
- Uses Tavily API for real-time financial data
- Returns top 3 search results with titles and content snippets
- Gracefully handles missing API key with a helpful message

### Test Scenarios (test_agent.py)

| Test | Query | Expected Behavior |
| :--- | :---- | :---------------- |
| **Test 1** | "What was Tesla's revenue and net income in 2023?" | RAG retrieves from public 10-K data |
| **Test 2** | "What is Apple's revenue as a percentage of Tesla's?" | RAG lookup + Calculator computation |
| **Test 3** | "What is Project Phoenix?" (intern vs admin) | Intern blocked, Admin sees confidential data |

---

## Project File Structure

```
AI_Financial_Analyst/
├── .env                    # API keys (GOOGLE_API_KEY, TAVILY_API_KEY)
├── requirements.txt        # Python dependencies
├── architecture.txt        # Original build plan
├── architecture.md         # This file — full build documentation
│
├── data/
│   ├── public/             # Public 10-K filings (access_level: "all")
│   │   ├── tesla_10k.pdf
│   │   ├── apple_10k.pdf
│   │   └── nvidia_10k.pdf
│   └── confidential/       # Internal memos (access_level: "admin")
│       ├── q4_strategy.pdf
│       ├── ceo_memo.pdf
│       └── legal_update.pdf
│
├── chroma_db/              # ChromaDB persistent storage (generated)
│
├── generate_samples.py     # Creates sample PDF documents
├── ingest.py               # Ingestion pipeline (PDF → embeddings → ChromaDB)
├── query_test.py           # Week 1 RBAC test script
├── peek_db.py              # Database inspection utility
├── list_models.py          # Gemini model discovery utility
│
├── agent.py                # LangGraph agent (Planner → Executor → Synthesizer)
├── test_agent.py           # Week 2 agent test scenarios
│
├── tools/
│   ├── __init__.py
│   ├── rag_tool.py         # RAG search with RBAC
│   ├── calculator_tool.py  # Safe math evaluator
│   └── web_search_tool.py  # Tavily web search
│
└── tf-env-39/              # Python 3.9 virtual environment
```

---

## Dependencies

```
llama-index-core
llama-index-llms-google-genai
llama-index-embeddings-google-genai
llama-index-vector-stores-chroma
llama-index-readers-file
google-generativeai
google-genai
python-dotenv
pypdf
reportlab
langgraph
langchain-core
tavily-python
```

---

## How to Run

```bash
# 1. Activate virtual environment
source tf-env-39/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up .env file with your API keys
# GOOGLE_API_KEY=your_key
# TAVILY_API_KEY=your_key (optional, for web search)

# 4. Generate sample documents
python3 generate_samples.py

# 5. Ingest documents into ChromaDB
python3 ingest.py

# 6. Test RBAC (Week 1)
python3 query_test.py

# 7. Test the full agent (Week 2)
python3 test_agent.py

# 8. Interactive mode
python3 agent.py
```

---

## Budget

| Item             | Service              | Cost                        |
| :--------------- | :------------------- | :-------------------------- |
| **LLM API**      | Google Gemini         | $0 (Free tier)             |
| **Vector DB**    | ChromaDB (local)      | $0                         |
| **Web Search**   | Tavily                | $0 (Free tier, 1k/mo)     |
| **Hosting**      | Local development     | $0                         |
| **Total**        |                       | **$0**                     |

---

## Week 3: Security & API (The Fortress)

### What Was Built

A production-ready FastAPI web layer with JWT authentication, RBAC enforcement,
prompt injection guardrails, SSE streaming, and Docker secrets management.

### Files Created

| File | Purpose |
| :--- | :------ |
| `api/app.py` | FastAPI app factory with `/auth/login`, `/query`, `/query/stream`, `/health` routes |
| `api/auth.py` | JWT token creation/validation + SHA-256 hashed user store |
| `api/models.py` | Pydantic schemas for request/response validation |
| `api/guardrails.py` | Regex-based prompt injection detection (12 attack patterns) |
| `server.py` | ASGI entry point for Uvicorn / Cloud Run (`uvicorn server:app`) |
| `config/settings.py` | Updated with `resolve_secret()` for Docker secrets priority chain |
| `Dockerfile` | Multi-stage build (Python 3.9-slim, ~150MB image) |
| `docker-compose.yml` | Dev profile (uses .env) + prod profile (uses Docker secrets) |
| `.dockerignore` | Excludes venv, tests, data, secrets from the image |
| `tests/test_auth.py` | 8 tests: user auth, JWT create/decode/expiry/tamper |
| `tests/test_api.py` | 9 tests: all endpoints, auth flow, guardrails, mocked agent |
| `tests/test_guardrails.py` | 16 tests: clean queries pass, 10 injection attacks blocked |
| `tests/test_secrets.py` | 4 tests: Docker secrets > env var > default priority |

### API Endpoints

| Method | Path | Auth | Description |
| :----- | :--- | :--- | :---------- |
| POST | `/auth/login` | None | Returns JWT token with role embedded |
| POST | `/query` | JWT | Synchronous query → full response |
| POST | `/query/stream` | JWT | SSE streaming → status events + answer |
| GET | `/health` | None | Health check with version |
| GET | `/` | None | Serves the chat UI |

### Authentication Flow

```
Client                        Server
  │                              │
  │  POST /auth/login            │
  │  {username, password}  ───►  │  authenticate_user()
  │                              │  create_token(role)
  │  ◄───  {access_token, role}  │
  │                              │
  │  POST /query                 │
  │  Authorization: Bearer xxx   │
  │  {question}            ───►  │  decode_token() → role
  │                              │  check_prompt_injection()
  │                              │  agent.run(question, role)
  │  ◄───  {answer, role}       │
```

### Secrets Management

The `resolve_secret()` function implements a priority chain:

1. **Docker secrets** — reads from `/run/secrets/<name>` (Docker Swarm/Compose)
2. **Environment variables** — `os.getenv()` (Cloud Run, CI/CD)
3. **Default value** — hardcoded fallback (local dev)

```python
def resolve_secret(name: str, default: str = "") -> str:
    secrets_path = f"/run/secrets/{name.lower()}"
    if os.path.isfile(secrets_path):
        with open(secrets_path) as f:
            return f.read().strip()
    return os.getenv(name, default)
```

### Prompt Injection Guardrails

The guardrails module detects 12 common prompt injection patterns:
- "ignore all previous instructions"
- "you are now a ..."
- "disregard your rules"
- "system prompt:" / `<system>` tags
- "DAN mode" / "do anything now"
- And 6 more patterns

Flagged queries get a 400 response before reaching the LLM, preventing data exfiltration.

### Docker Architecture

```
┌─────────────────────────────────────┐
│  Docker Image (python:3.9-slim)     │
│                                     │
│  Stage 1: builder                   │
│    └── pip install → /install       │
│                                     │
│  Stage 2: production                │
│    ├── /app/config/                 │
│    ├── /app/database/               │
│    ├── /app/ingestion/              │
│    ├── /app/tools/                  │
│    ├── /app/agent/                  │
│    ├── /app/api/                    │
│    ├── /app/static/                 │
│    ├── /app/server.py               │
│    └── uvicorn server:app           │
│                                     │
│  No .env baked in                   │
│  Secrets via /run/secrets/ or ENV   │
└─────────────────────────────────────┘
```

---

## Week 4: UI & Evaluation (The Product)

### What Was Built

A browser-based chat interface and an automated evaluation suite for measuring agent quality.

### Files Created

| File | Purpose |
| :--- | :------ |
| `static/index.html` | Single-page chat UI with login, role badge, dark theme |
| `evaluation/__init__.py` | Package init |
| `evaluation/eval_suite.py` | 5 eval cases testing RAG, calculator, RBAC, multi-tool |

### Chat UI Features

- **Login screen** — username/password form, demo credentials shown
- **Role badge** — color-coded (amber for admin, green for intern) in the header
- **Chat messages** — user messages right-aligned (indigo), bot messages left-aligned (dark surface)
- **Error handling** — connection errors and guardrail rejections shown inline
- **Logout** — clears token and returns to login
- **Responsive** — works on desktop and mobile
- **Dark theme** — modern dark color palette, no external dependencies

### Evaluation Suite

Runs 5 test cases against the live agent and scores responses:

| Test Case | Role | Checks |
| :-------- | :--- | :----- |
| `basic_revenue_query` | admin | Expected keywords: "revenue", "apple" |
| `calculator_usage` | intern | Expected: "375000" or "375,000" |
| `rbac_intern_confidential` | intern | Forbidden: "salary", "compensation" |
| `rbac_admin_full_access` | admin | No restrictions on response |
| `multi_tool_question` | intern | Expected: "25", "margin", "profit" |

Each case reports PASS/FAIL with duration and reason.

```bash
python -m evaluation.eval_suite
```

---

## Full Test Coverage

| Test File | Count | What It Covers |
| :-------- | :---: | :------------- |
| `test_calculator.py` | 23 | Arithmetic, functions, safety (no eval) |
| `test_config.py` | 6 | Defaults, env loading, validation |
| `test_rbac.py` | 5 | Metadata filter logic per role |
| `test_tools_interface.py` | 6 | BaseTool contract, web search degradation |
| `test_agent_integration.py` | 4 | Full pipeline (requires API) |
| `test_auth.py` | 8 | User auth, JWT lifecycle |
| `test_api.py` | 9 | All API endpoints with mocked agent |
| `test_guardrails.py` | 16 | Clean queries + injection attacks |
| `test_secrets.py` | 4 | Docker secrets priority chain |
| **Total** | **81** | **77 pass offline, 4 require API** |
