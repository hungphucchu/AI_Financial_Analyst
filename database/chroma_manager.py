"""
Wrapper around ChromaDB so the rest of the app never imports chromadb directly.

"""

import json
import chromadb
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext

from config.settings import Settings


class ChromaManager:
    """Manages all ChromaDB operations: connections, collections, and storage contexts.

    Attributes:
        settings: Application configuration (db path, collection name, etc.).
        client: The ChromaDB PersistentClient that reads/writes to disk.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        # PersistentClient uses ./chroma_db/ as the database location.
        # First run: creates the folder + chroma.sqlite3 (empty database).
        # Subsequent runs: opens existing data — no re-ingestion needed.
        self.client = chromadb.PersistentClient(path=settings.chroma_db_path)

    def get_or_create_collection(self) -> chromadb.Collection:
        # Returns the collection if it exists, creates an empty one if not.
        # Used by the ingestion pipeline (needs to create on first run).
        # RAGTool uses get_collection() instead, which fails if data is missing.
        return self.client.get_or_create_collection(
            self.settings.chroma_collection_name
        )

    def recreate_collection(self) -> chromadb.Collection:
        """Drop and recreate the configured collection.

        Use this when switching embedding models with different vector dimensions.
        """
        try:
            self.client.delete_collection(self.settings.chroma_collection_name)
        except Exception:
            # It's okay if collection doesn't exist yet.
            pass
        return self.get_or_create_collection()

    def get_collection(self) -> chromadb.Collection:
        """Get an existing collection. Fails clearly if it's missing.

        Returns:
            The ChromaDB Collection object.

        Raises:
            ValueError: If the collection hasn't been created yet.
        """
        try:
            return self.client.get_collection(
                self.settings.chroma_collection_name
            )
        except Exception as e:
            raise ValueError(
                f"Collection '{self.settings.chroma_collection_name}' not found. "
                "Run the ingestion pipeline first."
            ) from e

    def get_vector_store(self, collection: chromadb.Collection) -> ChromaVectorStore:
        """Wrap a ChromaDB collection in LlamaIndex's vector store interface.

        Args:
            collection: An existing ChromaDB collection.

        Returns:
            A ChromaVectorStore that LlamaIndex can query against.
        """
        # Adapter pattern: wraps ChromaDB collection in LlamaIndex's interface.
        # LlamaIndex can't talk to ChromaDB directly — this is the translator.
        return ChromaVectorStore(chroma_collection=collection)

    def get_storage_context(self, collection: chromadb.Collection) -> StorageContext:
        """Create a LlamaIndex StorageContext for writing documents into a collection.

        Args:
            collection: The target ChromaDB collection.

        Returns:
            A StorageContext configured to write into the given collection.
        """
        vector_store = self.get_vector_store(collection)
        # StorageContext tells LlamaIndex WHERE to write embedded chunks.
        # Without it, vectors go to memory (lost on restart).
        # With it, vectors go through the adapter into ChromaDB on disk.
        # Used by ingestion pipeline (write). RAGTool uses get_vector_store() (read).
        return StorageContext.from_defaults(vector_store=vector_store)

    def peek(self, limit: int = 5) -> None:
        """Print a quick summary of what's in the database.

        Args:
            limit: Number of chunks to display. Defaults to 5.
        """
        try:
            collection = self.get_collection()
        except ValueError as e:
            print(f"Error: {e}")
            return

        count = collection.count()
        print(f"--- Database Stats ---")
        print(f"Total Chunks: {count}\n")

        if count == 0:
            print("Database is empty.")
            return

        results = collection.get(limit=limit)
        print(f"--- Top {limit} Chunks ---")
        for i in range(len(results["ids"])):
            print(f"ID: {results['ids'][i]}")
            print(f"Metadata: {json.dumps(results['metadatas'][i], indent=2)}")
            snippet = results["documents"][i][:100].replace("\n", " ")
            print(f"Text: {snippet}...")
            print("-" * 40)
