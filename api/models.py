"""
Pydantic schemas for API request/response validation.
"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Credentials sent to ``POST /auth/login``.

    Attributes:
        username: The user's login name (e.g., "admin" or "intern").
        password: The user's password in plaintext (sent over HTTPS).
    """

    username: str
    password: str


class LoginResponse(BaseModel):
    """Returned after successful authentication.

    Attributes:
        access_token: JWT token to include in subsequent requests
                      as ``Authorization: Bearer <token>``.
        token_type: Always "bearer" (OAuth2 convention).
        role: The authenticated user's role ("admin" or "intern").
    """

    access_token: str
    token_type: str = "bearer"
    role: str


class QueryRequest(BaseModel):
    """Question sent to ``POST /query`` or ``POST /query/stream``.

    Attributes:
        question: The user's question about financial data.
                  Must be 1-2000 characters (guards against empty or huge payloads).
    """

    question: str = Field(..., min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    """The agent's answer returned from ``POST /query``.

    Attributes:
        answer: The synthesized response from the agent pipeline.
        role: The role used for this query (affects what documents were accessible).
        question: Echo of the original question (useful for logging/debugging).
    """

    answer: str
    role: str
    question: str


class HealthResponse(BaseModel):
    """Returned from ``GET /health``.

    Attributes:
        status: Always "ok" if the server is running.
        version: The API version string (e.g., "1.0.0").
    """

    status: str
    version: str
