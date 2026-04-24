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
        qwen_api_key: Required. Qwen API key for LLM generation.
        qwen_base_url: OpenAI-compatible endpoint URL for Qwen API.
        tavily_api_key: Optional. Enables the web search tool for live data.
        llm_model: Qwen model name for text generation.
        embedding_model: Local sentence-transformers model name for embeddings.
        embedding_batch_size: Batch size for local embedding generation.
        normalize_embeddings: Whether to L2-normalize vectors before storage/query.
        llm_temperature: Lower = more deterministic. 0.1 keeps financial answers precise.
        llm_context_window: Max input tokens the LLM can handle. Passed to OpenAILike
            since custom endpoints don't advertise a default context size.
        chroma_db_path: Where ChromaDB stores its data on disk.
        chroma_collection_name: Name of the vector collection inside ChromaDB.
        max_retries: How many times to retry on Qwen 429 (rate limit) errors.
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

    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    tavily_api_key: str = ""

    llm_model: str = "qwen-plus"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_batch_size: int = 64
    normalize_embeddings: bool = True
    llm_temperature: float = 0.1
    llm_context_window: int = 32000

    chroma_db_path: str = "./chroma_db"
    chroma_collection_name: str = "financial_analyst"

    data_public_dir: str = "./data/public"
    data_confidential_dir: str = "./data/confidential"

    max_retries: int = 6
    retry_base_delay: int = 10
    retry_max_delay: int = 120
    ingestion_batch_size: int = 10
    inter_tool_delay: float = 3.0

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
        # Tier 1: Docker secrets (most secure, mounted as read-only files)
        secrets_path = f"/run/secrets/{name.lower()}"
        if os.path.isfile(secrets_path):
            with open(secrets_path) as f:
                return f.read().strip()
        # Tier 2: environment variable (Cloud Run, .env via python-dotenv)
        # Tier 3: default value (fallback, usually empty string)
        return os.getenv(name, default)

    @classmethod
    def from_env(cls) -> "Settings":
        """Create a Settings instance from environment variables and secrets.

        Returns:
            A fully configured Settings instance ready for use.
        """
        load_dotenv()

        qwen_key = cls.resolve_secret("QWEN_API_KEY")
        if not qwen_key:
            raise ValueError(
                "QWEN_API_KEY is required. "
                "Set it in .env, environment, or /run/secrets/qwen_api_key."
            )

        return cls(
            qwen_api_key=qwen_key,
            qwen_base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ),
            llm_model=os.getenv("QWEN_MODEL", "qwen-plus"),
            embedding_model=os.getenv(
                "LOCAL_EMBEDDING_MODEL",
                "sentence-transformers/all-MiniLM-L6-v2",
            ),
            embedding_batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "64")),
            normalize_embeddings=os.getenv("NORMALIZE_EMBEDDINGS", "true").lower() == "true",
            tavily_api_key=cls.resolve_secret("TAVILY_API_KEY"),
            jwt_secret=cls.resolve_secret("JWT_SECRET", "change-me-in-production"),
            api_port=int(os.getenv("PORT", "8000")),
        )
