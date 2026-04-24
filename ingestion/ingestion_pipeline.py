"""
Reads PDFs, stamps them with RBAC metadata, embeds them, and stores in ChromaDB.
This is the bridge between raw PDF files and the searchable vector database.
After this pipeline runs, the RAG tool can answer questions from the documents.
"""

import os

from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings as LlamaSettings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai_like import OpenAILike

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
        # Embeddings are generated locally by sentence-transformers, so no API
        # calls are made during ingestion vector generation.
        LlamaSettings.embed_model = HuggingFaceEmbedding(
            model_name=self.settings.embedding_model,
            embed_batch_size=self.settings.embedding_batch_size,
            normalize=self.settings.normalize_embeddings,
        )
        # Use OpenAILike (not OpenAI) so custom Qwen model names like
        # "qwen-plus" or "Qwen/Qwen3-8B" aren't rejected by LlamaIndex's
        # hardcoded OpenAI model allowlist.
        LlamaSettings.llm = OpenAILike(
            model=self.settings.llm_model,
            api_key=self.settings.qwen_api_key,
            api_base=self.settings.qwen_base_url,
            is_chat_model=True,
            context_window=self.settings.llm_context_window,
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

        # This single call does all the heavy lifting:
        # 1. Splits documents into smaller text chunks
        # 2. Uses the local sentence-transformers model to embed each chunk
        # 3. Writes vectors + text + metadata into ChromaDB (via storage_context)
        # Batch size of 10 avoids Gemini rate limits during embedding.
        try:
            index = VectorStoreIndex.from_documents(
                all_docs,
                storage_context=storage_context,
                show_progress=True,
                insert_batch_size=self.settings.ingestion_batch_size,
            )
        except Exception as e:
            message = str(e)
            # Happens when an old Chroma collection was created with a different
            # embedding model dimension (e.g. 3072 before, 384 now).
            if "expecting embedding with dimension" in message:
                print(
                    "Detected embedding dimension mismatch in existing collection. "
                    "Recreating collection and retrying ingestion..."
                )
                collection = self.db.recreate_collection()
                storage_context = self.db.get_storage_context(collection)
                index = VectorStoreIndex.from_documents(
                    all_docs,
                    storage_context=storage_context,
                    show_progress=True,
                    insert_batch_size=self.settings.ingestion_batch_size,
                )
            else:
                raise ValueError(
                    "Embedding failed. Check LOCAL_EMBEDDING_MODEL and your local "
                    "sentence-transformers installation."
                ) from e

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
