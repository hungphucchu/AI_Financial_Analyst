# Secure Enterprise RAG Agent — Internal Financial Analyst

A multi-tool AI financial analyst that uses Retrieval-Augmented Generation (RAG) to answer questions from internal financial documents, enforces Role-Based Access Control (RBAC) at the vector database level, and orchestrates tools through a LangGraph stateful agent. Includes a FastAPI web layer with JWT auth, SSE streaming, prompt injection guardrails, and a chat UI — all containerized for Cloud Run deployment.

Portfolio: [https://hungphucchu.github.io/AI_Financial_Analyst/](https://hungphucchu.github.io/AI_Financial_Analyst/)

## Project Structure

```
AI_Financial_Analyst/
├── main.py                         # CLI entry point (generate, ingest, peek, chat, serve)
├── server.py                       # ASGI entry point for uvicorn / Cloud Run
│
├── config/
│   ├── __init__.py
│   └── settings.py                 # Settings dataclass + resolve_secret() for Docker secrets
│
├── database/
│   ├── __init__.py
│   └── chroma_manager.py           # ChromaManager — vector DB connection, collection access, peek
│
├── ingestion/
│   ├── __init__.py
│   ├── sample_document_generator.py # SampleDocumentGenerator — creates test PDF documents
│   └── ingestion_pipeline.py       # IngestionPipeline — PDF parsing, metadata tagging, embedding
│
├── tools/
│   ├── __init__.py
│   ├── base_tool.py                # BaseTool — abstract interface all tools implement
│   ├── rag_tool.py                 # RAGTool — semantic search with RBAC metadata filtering
│   ├── calculator_tool.py          # CalculatorTool — safe AST-based math evaluator (no eval)
│   └── web_search_tool.py          # WebSearchTool — real-time data via Tavily API
│
├── agent/
│   ├── __init__.py
│   ├── agent_state.py              # AgentState — TypedDict passed between graph nodes
│   ├── prompts.py                  # System prompts for Planner and Synthesizer
│   ├── gemini_client.py            # GeminiClient — Qwen/OpenAI-compatible API calls with retry logic
│   ├── agent_nodes.py              # AgentNodes — planner, tool_executor, synthesizer nodes
│   └── financial_analyst_agent.py  # FinancialAnalystAgent — LangGraph orchestration + run()
│
├── api/
│   ├── __init__.py
│   ├── app.py                      # FastAPI app factory with all routes
│   ├── auth.py                     # JWT authentication + user store
│   ├── models.py                   # Pydantic request/response schemas
│   └── guardrails.py               # Prompt injection detection
│
├── static/
│   └── index.html                  # Chat UI (served by FastAPI)
│
├── evaluation/
│   ├── __init__.py
│   └── eval_suite.py               # Automated evaluation with test cases + scoring
│
├── tests/
│   ├── __init__.py
│   ├── test_calculator.py          # 23 tests: arithmetic, functions, safety
│   ├── test_config.py              # 6 tests: defaults, env loading, validation
│   ├── test_rbac.py                # 5 tests: metadata filter logic per role
│   ├── test_tools_interface.py     # 6 tests: BaseTool contract, graceful degradation
│   ├── test_agent_integration.py   # 4 integration tests: RAG, multi-tool, RBAC
│   ├── test_auth.py                # 8 tests: user auth, JWT create/decode/expiry
│   ├── test_api.py                 # 9 tests: endpoints, auth flow, guardrails
│   ├── test_guardrails.py          # 16 tests: clean queries pass, injections blocked
│   └── test_secrets.py             # 4 tests: Docker secrets > env var > default
│
├── .env                            # API keys (not committed)
├── .gitignore
├── .dockerignore
├── Dockerfile                      # Multi-stage build for Cloud Run
├── docker-compose.yml              # Local dev + prod profiles with Docker secrets
├── requirements.txt
├── architecture.txt                # Original build plan
└── architecture.md                 # Detailed build documentation
```

## Tech Stack

| Layer              | Technology                      |
| :----------------- | :------------------------------ |
| LLM                | Qwen (via OpenAI-compatible API) |
| Embeddings         | text-embedding-v3               |
| RAG Framework      | LlamaIndex                      |
| Vector Database    | ChromaDB (local, persistent)    |
| Agent Orchestration| LangGraph                       |
| Web Search         | Tavily API                      |
| Calculator         | Custom AST-based safe evaluator |
| Web API            | FastAPI + Uvicorn               |
| Auth               | JWT (PyJWT)                     |
| Streaming          | Server-Sent Events (SSE)        |
| Frontend           | Vanilla HTML/CSS/JS             |
| Containerization   | Docker (multi-stage)            |
| Deployment         | GCP Cloud Run ready             |
| Language           | Python 3.9                      |

## Setup

```bash
# Create and activate virtual environment
python3 -m venv tf-env-39
source tf-env-39/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Edit .env with your QWEN_API_KEY (required) and TAVILY_API_KEY (optional)
```

## Usage

```bash
python main.py generate   # Create sample PDF documents
python main.py ingest     # Parse PDFs, embed, and store in ChromaDB
python main.py peek       # Inspect ChromaDB contents
python main.py chat       # Interactive agent with role switching
python main.py serve      # Start the FastAPI web server on port 8000
```

In chat mode, type `role:admin` or `role:intern` to switch roles, and `quit` to exit.

### Web API

```bash
# Start the server
python main.py serve

# Login (get JWT token)
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# Query with token
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"question": "What was Tesla revenue in 2023?"}'

# SSE streaming
curl -X POST http://localhost:8000/query/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"question": "What was Tesla revenue in 2023?"}'

# Health check
curl http://localhost:8000/health
```

Or open http://localhost:8000 in a browser for the chat UI.

### Sample Questions

Try these to see RBAC in action — login as both **admin** and **intern** to compare results:

| Question | Admin sees | Intern sees |
| :------- | :--------- | :---------- |
| "What is Project Phoenix?" | Full confidential acquisition plan | "No relevant data found" or public-only info |
| "Show me the CEO memo on hardware sales" | Complete CEO memo with forecasts | Blocked — confidential document |
| "What is the pending litigation settlement amount?" | $500M settlement details from legal update | No access to legal documents |
| "What was Tesla's revenue in 2023?" | $96.8B from public 10-K | Same — public data, both roles see it |
| "Compare Apple and NVIDIA revenue" | Full comparison from public filings | Same — public data |

**Calculator questions** (works for both roles):
- "What is 15% of 2,500,000?"
- "If revenue is 1,000,000 and costs are 750,000, what is the profit margin?"

**Real-time web search questions** (requires `TAVILY_API_KEY`):
- "What is the current stock price of Apple?"
- "What are the latest earnings results for NVIDIA?"
- "What is the S&P 500 index today?"

The agent automatically picks the right tool — RAG for internal docs, calculator for math, web search for live market data.

## Docker

```bash
# Local dev (uses .env file)
docker-compose up --build

# Production (uses Docker secrets)
mkdir -p secrets
echo "your-qwen-api-key" > secrets/qwen_api_key
echo "your-tavily-api-key" > secrets/tavily_api_key
echo "your-jwt-secret-32chars-min" > secrets/jwt_secret
docker-compose --profile prod up --build
```

## Secrets Management

The app loads secrets with a priority chain: **Docker secrets > environment variables > .env file**.

| Method | When to use | How |
| :----- | :---------- | :-- |
| `.env` file | Local development | Put keys in `.env`, `python-dotenv` loads them |
| Environment vars | CI/CD, Cloud Run | Set via `gcloud run deploy --set-env-vars` |
| Docker secrets | Docker Swarm / Compose | Mount files in `/run/secrets/` |

## Testing

```bash
# All unit tests (no API key needed, 77 tests)
pytest tests/ -v --ignore=tests/test_agent_integration.py

# Full test suite including integration (requires QWEN_API_KEY + ingested data)
pytest tests/ -v -s

# Evaluation suite (requires QWEN_API_KEY + ingested data)
python -m evaluation.eval_suite
```

## Agent Architecture

```
User Query → [Planner] → [Tool Executor] → [Synthesizer] → Answer
                │              │
                │         ┌────┼────────┐
                │         │    │        │
                ▼         ▼    ▼        ▼
              Qwen LLM   RAG  Calc  Web Search
            (JSON plan)   │
                          ▼
                      ChromaDB
                    + RBAC Filter
```

- **Planner**: Qwen decides which tools to call and with what inputs
- **Tool Executor**: Runs selected tools, passes user role to RAG for RBAC
- **Synthesizer**: Qwen combines tool outputs into a professional answer

## RBAC

Access control is enforced at the vector database query level:

- **Admin**: No filter — sees all documents (public + confidential)
- **Intern / any other role**: `MetadataFilter(access_level="all")` — only public documents returned

## Architecture

For detailed documentation of every component built across all 4 weeks — including system diagrams, RBAC implementation, ingestion pipeline, agent graph, API endpoints, Docker architecture, and the full test coverage breakdown — see [ARCHITECTURE.md](ARCHITECTURE.md).

## Cloud Run Deployment

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/financial-analyst

# Deploy to Cloud Run
gcloud run deploy financial-analyst \
  --image gcr.io/YOUR_PROJECT_ID/financial-analyst \
  --platform managed \
  --region us-central1 \
  --set-env-vars QWEN_API_KEY=your-key,QWEN_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1,QWEN_MODEL=qwen-plus,TAVILY_API_KEY=your-key,JWT_SECRET=your-secret \
  --allow-unauthenticated
```
