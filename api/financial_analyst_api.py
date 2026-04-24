"""

Routes:
    POST /auth/login     — Authenticate and get a JWT token
    POST /query          — Send a question, get a full response (synchronous)
    POST /query/stream   — Send a question, get SSE events (streaming)
    GET  /health         — Health check (no auth required)
    GET  /               — Serves the chat UI (static/index.html)

Usage:
    api = FinancialAnalystAPI(settings)
    app = api.app  # the FastAPI instance for uvicorn
"""

import asyncio
from functools import partial

from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from api.models import (
    LoginRequest, LoginResponse,
    QueryRequest, QueryResponse,
)
from api.jwt_auth_service import JwtAuthService
from api.prompt_guardrail import PromptGuardrail
from config.settings import Settings
from agent.financial_analyst_agent import FinancialAnalystAgent

APP_VERSION = "1.0.0"


class FinancialAnalystAPI:
    """Wraps the FastAPI application with auth, guardrails, and agent routing.

    Owns all the dependencies (agent, auth service, guardrail) and
    registers all routes in ``register_routes()``. The compiled FastAPI
    app is available via ``self.app``.

    Attributes:
        settings: Application configuration.
        auth: JwtAuthService for login and token validation.
        guardrail: PromptGuardrail for prompt injection detection.
        agent: FinancialAnalystAgent for processing queries.
        app: The FastAPI instance with all routes registered.
    """

    def __init__(self, settings: Settings):
        """Set up the API with all its dependencies.

        Args:
            settings: Must include API keys, JWT config, and model names.
        """
        self.settings = settings
        self.auth = JwtAuthService(settings)
        self.guardrail = PromptGuardrail()
        self.agent = FinancialAnalystAgent(settings)
        self.app = self.create_app()

    def create_app(self) -> FastAPI:
        """Build the FastAPI instance with middleware and routes.

        Returns:
            A fully configured FastAPI app ready to serve requests.
        """
        app = FastAPI(
            title="Financial Analyst API",
            version=APP_VERSION,
            description="RAG-powered financial analysis with RBAC",
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        self.register_routes(app)
        return app

    def get_role_from_token(self, authorization: str) -> str:
        """Extract and validate the JWT from the Authorization header.

        Args:
            authorization: The raw Authorization header value
                           (e.g., "Bearer eyJhbG...").

        Returns:
            The user's role string (e.g., "admin" or "intern").

        Raises:
            HTTPException: 401 if the token is missing, malformed,
                           expired, or invalid.
        """
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid token")

        token = authorization.split(" ", 1)[1]
        payload = self.auth.decode_token(token)
        if payload is None:
            raise HTTPException(status_code=401, detail="Token expired or invalid")

        return payload.get("role", "intern")

    def register_routes(self, app: FastAPI) -> None:
        """Register all API routes on the given FastAPI app.

        Uses closures to capture ``self`` so route handlers can access
        the auth service, guardrail, and agent.

        Args:
            app: The FastAPI instance to register routes on.
        """
        auth = self.auth
        guardrail = self.guardrail
        agent = self.agent

        @app.post("/auth/login", response_model=LoginResponse)
        def login(req: LoginRequest):
            """Authenticate a user and return a JWT token."""
            user = auth.authenticate(req.username, req.password)
            if user is None:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            token = auth.create_token(user["username"], user["role"])
            return LoginResponse(access_token=token, role=user["role"])

        @app.post("/query", response_model=QueryResponse)
        def query(req: QueryRequest, authorization: str = Header(None)):
            """Process a financial question through the full agent pipeline."""
            role = self.get_role_from_token(authorization)

            injection = guardrail.check(req.question)
            if injection:
                raise HTTPException(status_code=400, detail=injection)

            try:
                answer = agent.run(req.question, role=role)
            except RuntimeError as e:
                if "quota" in str(e).lower() or "retries" in str(e).lower():
                    answer = "The Qwen API rate limit has been reached. Please wait 1-2 minutes and try again."
                else:
                    raise HTTPException(status_code=500, detail=str(e))
            return QueryResponse(answer=answer, role=role, question=req.question)

        # SSE streaming endpoint — sends events to the browser in real time
        # instead of waiting for the full answer. Frontend shows status updates
        # ("Planning...", "Complete") as they happen via EventSource.
        @app.post("/query/stream")
        async def query_stream(req: QueryRequest, authorization: str = Header(None)):
            """Stream the agent's response via Server-Sent Events (SSE)."""
            role = self.get_role_from_token(authorization)  # JWT → role

            # First line of defense: block prompt injection before it reaches the LLM
            injection = guardrail.check(req.question)
            if injection:
                raise HTTPException(status_code=400, detail=injection)

            async def event_generator():
                yield {"event": "status", "data": "Planning..."}  # sent immediately to browser

                try:
                    # Agent pipeline is sync (blocks 10-20s for LLM API calls).
                    # FastAPI is async — calling agent.run() directly would freeze
                    # the entire server for all users. run_in_executor pushes it to
                    # a separate thread so the event loop stays free to serve others.
                    loop = asyncio.get_running_loop()          # get the async event loop
                    run_fn = partial(agent.run, req.question, role=role)  # package sync fn + args
                    answer = await loop.run_in_executor(None, run_fn)    # run in thread, await result

                    yield {"event": "status", "data": "Complete"}
                    yield {"event": "answer", "data": answer}
                except RuntimeError as e:
                    # Catch "Max retries reached — Qwen quota exhausted" from gemini_client.py
                    if "quota" in str(e).lower() or "retries" in str(e).lower():
                        yield {"event": "answer", "data": "The Qwen API rate limit has been reached. Please wait 1-2 minutes and try again."}
                    else:
                        yield {"event": "answer", "data": f"Error: {e}"}
                except Exception as e:
                    yield {"event": "answer", "data": f"An error occurred: {e}"}

            # EventSourceResponse keeps the HTTP connection open and sends each
            # yielded event to the browser as it happens (Server-Sent Events).
            return EventSourceResponse(event_generator())

        @app.get("/health")
        def health():
            """Health check — returns 200 with data status."""
            try:
                from database.chroma_manager import ChromaManager
                db = ChromaManager(self.settings)
                collection = db.get_collection()
                doc_count = collection.count()
                data_ready = doc_count > 0
            except Exception:
                doc_count = 0
                data_ready = False

            return {
                "status": "ok",
                "version": APP_VERSION,
                "data_ready": data_ready,
                "document_chunks": doc_count,
            }

        app.mount("/static", StaticFiles(directory="static"), name="static")

        @app.get("/")
        def serve_frontend():
            """Serve the chat UI at the root URL."""
            return FileResponse("static/index.html")
