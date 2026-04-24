"""
RAG (Retrieval-Augmented Generation) tool with RBAC enforcement.
Searches internal financial documents with role-based access control.

Function:
    This is where access control actually happens. When a user asks a question,
    this tool searches ChromaDB for relevant document chunks — but it filters
    results based on the user's role. Interns only see public documents;
    admins see everything. The filtering happens at the database level, so
    confidential chunks never even leave ChromaDB for unauthorized users.
"""

import time

from llama_index.core import VectorStoreIndex, Settings as LlamaSettings
from llama_index.core.vector_stores import MetadataFilters, MetadataFilter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike

from tools.base_tool import BaseTool
from config.settings import Settings
from database.chroma_manager import ChromaManager


class RAGTool(BaseTool):

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = ChromaManager(settings)

    @property
    def name(self) -> str:
        return "RAG_SEARCH"

    @property
    def description(self) -> str:
        return (
            "Search internal financial documents (10-K filings, confidential memos). "
            "Use for company financials, internal strategy, or historical data."
        )

    def execute(self, tool_input: str, **kwargs) -> str:
        """Search internal documents with RBAC filtering applied.

        Args:
            tool_input: The search query (e.g., "Tesla revenue 2023").
            **kwargs: Must include ``role`` ("admin" or "intern") for RBAC.

        Returns:
            The LLM-generated answer from retrieved document chunks,
            or an error message if something goes wrong.
        """
        # Extract user's role for RBAC filtering. Defaults to "intern" (least
        # privilege) so if no role is passed, only public documents are returned.
        role = kwargs.get("role", "intern")

        # Re-set LlamaIndex's global models before each query to avoid stale
        # config. Done here (not __init__) to skip API setup if RAG isn't used.
        self.configure_models()

        try:
            collection = self.db.get_collection()
        except ValueError:
            return "Error: No documents ingested yet. Run the ingestion pipeline first."

        vector_store = self.db.get_vector_store(collection)  # wrap ChromaDB for LlamaIndex
        index = VectorStoreIndex.from_vector_store(vector_store)  # build searchable index

        filters = self.build_filters(role)  # RBAC: admin=no filter, intern=public only
        query_engine = index.as_query_engine(filters=filters)  # attach filters to search engine

        return self.query_with_retry(query_engine, tool_input)

    def configure_models(self) -> None:
        # Set up two AI models on LlamaIndex's global config (LlamaSettings).
        # Once set, every LlamaIndex operation uses them automatically.
        #
        # NOTE: Embeddings are generated locally by sentence-transformers,
        # while synthesis/planning run on Qwen. LlamaIndex needs wrapper classes
        # for both steps of the RAG pipeline.

        # Embedding model:
        # Converts text into a vector (list of ~768 numbers).
        # Example: "Apple revenue" → [0.012, -0.834, 0.291, ..., 0.445]
        # ChromaDB compares this query vector against stored document vectors
        # using cosine similarity to find the most relevant chunks.
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name=self.settings.embedding_model,
            embed_batch_size=self.settings.embedding_batch_size,
            normalize=self.settings.normalize_embeddings,
        )
        # LLM (Qwen via OpenAI-compatible endpoint):
        # Takes the retrieved chunks + user's question and writes a natural
        # language answer. Without this, you'd get raw document text instead
        # of a synthesized response.
        # Example input:  chunks=["Apple reported $394B..."] + "What is revenue?"
        # Example output: "Apple's revenue was $394.3 billion in fiscal 2024."
        #
        # We use OpenAILike (not OpenAI) because LlamaIndex's OpenAI class
        # validates the model name against a hardcoded list of OpenAI models.
        # Qwen model names (e.g. "qwen-plus", "Qwen/Qwen3-8B") aren't in that
        # list. OpenAILike skips that check and just forwards requests to any
        # OpenAI-compatible endpoint.
        LlamaSettings.llm = OpenAILike(
            model=self.settings.llm_model,
            api_key=self.settings.qwen_api_key,
            api_base=self.settings.qwen_base_url,
            is_chat_model=True,
            context_window=self.settings.llm_context_window,
        )

    @staticmethod
    def build_filters(role: str):
        """Create metadata filters based on the user's role.

        Args:
            role: The user's role string (e.g., "admin", "intern").

        Returns:
            A MetadataFilters object for non-admin roles, or None for admins.
        """
        if role == "admin":
            return None  # no filter → admin sees all documents
        # Non-admin: only return chunks tagged as public (access_level="all").
        # Confidential docs are excluded at the database level, not the prompt.
        return MetadataFilters(
            filters=[MetadataFilter(key="access_level", value="all")]
        )

    def query_with_retry(self, query_engine, query: str) -> str:
        """Execute a RAG query with exponential backoff for rate limits.

        Args:
            query_engine: A LlamaIndex query engine with filters already applied.
            query: The user's search question.

        Returns:
            The query response as a string, or an error message.
        """
        for attempt in range(self.settings.max_retries):
            try:
                response = query_engine.query(query)
                return str(response)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    wait = min(
                        2 ** attempt * self.settings.retry_base_delay,
                        self.settings.retry_max_delay,
                    )
                    time.sleep(wait)
                else:
                    return f"RAG Error: {e}"

        return "RAG tool is rate-limited. Please try again in a minute."
