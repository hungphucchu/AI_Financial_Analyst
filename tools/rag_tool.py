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
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

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
        role = kwargs.get("role", "intern")

        self.configure_models()

        try:
            collection = self.db.get_collection()
        except ValueError:
            return "Error: No documents ingested yet. Run the ingestion pipeline first."

        vector_store = self.db.get_vector_store(collection)
        index = VectorStoreIndex.from_vector_store(vector_store)

        filters = self.build_filters(role)
        query_engine = index.as_query_engine(filters=filters)

        return self.query_with_retry(query_engine, tool_input)

    def configure_models(self) -> None:
        LlamaSettings.embed_model = GoogleGenAIEmbedding(
            model_name=self.settings.embedding_model,
            api_key=self.settings.google_api_key,
        )
        LlamaSettings.llm = GoogleGenAI(
            model_name=self.settings.llm_model,
            api_key=self.settings.google_api_key,
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
            return None
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
