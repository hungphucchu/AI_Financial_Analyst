"""
Centralized configuration for the entire application.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    """Single source of truth for all application configuration.


    Attributes:
        google_api_key: Required. Gemini API key for LLM and embeddings.
        tavily_api_key: Optional. Enables the web search tool for live data.
        llm_model: Gemini model name. Changed here when Google deprecates one.
        embedding_model: Gemini embedding model for vectorizing documents.
        llm_temperature: Lower = more deterministic. 0.1 keeps financial answers precise.
        chroma_db_path: Where ChromaDB stores its data on disk.
        chroma_collection_name: Name of the vector collection inside ChromaDB.
        max_retries: How many times to retry on Gemini 429 (rate limit) errors.
        retry_base_delay: Starting delay in seconds. Doubles each retry (exponential backoff).
        retry_max_delay: Cap so we don't wait forever.
        ingestion_batch_size: Small batches during embedding to avoid hitting rate limits.
        inter_tool_delay: Seconds to pause between tool calls during agent execution.
        api_host: Network interface for the FastAPI server. 0.0.0.0 = all interfaces.
        api_port: Port number. Cloud Run sets this via the PORT env var.
        jwt_secret: HMAC key for signing JWT tokens. Must be overridden in production.
        jwt_algorithm: JWT signing algorithm. HS256 is the standard for symmetric keys.
        jwt_expiry_hours: How long a login token stays valid.
    """

    google_api_key: str = ""
    tavily_api_key: str = ""

    llm_model: str = "gemini-2.0-flash"
    embedding_model: str = "gemini-embedding-001"
    llm_temperature: float = 0.1

    chroma_db_path: str = "./chroma_db"
    chroma_collection_name: str = "financial_analyst"

    data_public_dir: str = "./data/public"
    data_confidential_dir: str = "./data/confidential"

    max_retries: int = 4
    retry_base_delay: int = 5
    retry_max_delay: int = 60
    ingestion_batch_size: int = 10
    inter_tool_delay: float = 2.0

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    @staticmethod
    def resolve_secret(name: str, default: str = "") -> str:
        """Load a secret value using a priority chain.


        Args:
            name: The secret name. Looked up as an env var (uppercase) and
                  as a Docker secret file (lowercase).
            default: Fallback value if neither source has it.

        Returns:
            The secret value as a string, stripped of whitespace.
        """
        secrets_path = f"/run/secrets/{name.lower()}"
        if os.path.isfile(secrets_path):
            with open(secrets_path) as f:
                return f.read().strip()
        return os.getenv(name, default)

    @classmethod
    def from_env(cls) -> "Settings":
        """Create a Settings instance from environment variables and secrets.

        Returns:
            A fully configured Settings instance ready for use.
        """
        load_dotenv()

        google_key = cls.resolve_secret("GOOGLE_API_KEY")
        if not google_key:
            raise ValueError(
                "GOOGLE_API_KEY is required. "
                "Set it in .env, environment, or /run/secrets/google_api_key."
            )

        return cls(
            google_api_key=google_key,
            tavily_api_key=cls.resolve_secret("TAVILY_API_KEY"),
            jwt_secret=cls.resolve_secret("JWT_SECRET", "change-me-in-production"),
            api_port=int(os.getenv("PORT", "8000")),
        )
