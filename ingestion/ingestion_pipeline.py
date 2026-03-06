"""
Reads PDFs, stamps them with RBAC metadata, embeds them, and stores in ChromaDB.
This is the bridge between raw PDF files and the searchable vector database.
After this pipeline runs, the RAG tool can answer questions from the documents.
"""

import os

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings as LlamaSettings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.llms.google_genai import GoogleGenAI

from config.settings import Settings
from database.chroma_manager import ChromaManager


class IngestionPipeline:
    ACCESS_PUBLIC = "all"
    ACCESS_ADMIN = "admin"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = ChromaManager(settings)
        self.configure_llama_index()

    def configure_llama_index(self) -> None:
        LlamaSettings.embed_model = GoogleGenAIEmbedding(
            model_name=self.settings.embedding_model,
            api_key=self.settings.google_api_key,
        )
        LlamaSettings.llm = GoogleGenAI(
            model_name=self.settings.llm_model,
            api_key=self.settings.google_api_key,
        )

    def run(self) -> VectorStoreIndex:
        """Execute the full ingestion pipeline.

        Returns:
            The VectorStoreIndex, which can be queried immediately.

        Raises:
            FileNotFoundError: If the data directories don't exist yet.
                Run ``python main.py generate`` to create sample data.
        """
        self.validate_data_dirs()

        collection = self.db.get_or_create_collection()
        storage_context = self.db.get_storage_context(collection)

        print("--- Ingesting Public Documents ---")
        public_docs = self.load_documents(
            self.settings.data_public_dir, self.ACCESS_PUBLIC
        )

        print("--- Ingesting Confidential Documents ---")
        confidential_docs = self.load_documents(
            self.settings.data_confidential_dir, self.ACCESS_ADMIN
        )

        all_docs = public_docs + confidential_docs

        index = VectorStoreIndex.from_documents(
            all_docs,
            storage_context=storage_context,
            show_progress=True,
            insert_batch_size=self.settings.ingestion_batch_size,
        )

        print("\nIngestion complete. Data stored in ChromaDB with RBAC metadata.")
        return index

    def load_documents(self, directory: str, access_level: str) -> list:
        """Load PDFs from a directory and tag them with an access level.

        Args:
            directory: Path to a folder of PDF files.
            access_level: Either "all" (public) or "admin" (confidential).

        Returns:
            List of LlamaIndex Document objects with metadata set.
        """
        reader = SimpleDirectoryReader(input_dir=directory)
        docs = reader.load_data()
        for doc in docs:
            doc.metadata["access_level"] = access_level
        return docs

    def validate_data_dirs(self) -> None:
        """Check that data directories exist before trying to read from them.

        Raises:
            FileNotFoundError: With a helpful message telling the user to
                run the generate command first.
        """
        for path in [self.settings.data_public_dir, self.settings.data_confidential_dir]:
            if not os.path.exists(path):
                raise FileNotFoundError(
                    f"Data directory not found: {path}. "
                    "Run 'python main.py generate' first."
                )
