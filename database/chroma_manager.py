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
        self.client = chromadb.PersistentClient(path=settings.chroma_db_path)

    def get_or_create_collection(self) -> chromadb.Collection:
        return self.client.get_or_create_collection(
            self.settings.chroma_collection_name
        )

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
        return ChromaVectorStore(chroma_collection=collection)

    def get_storage_context(self, collection: chromadb.Collection) -> StorageContext:
        """Create a LlamaIndex StorageContext for writing documents into a collection.

        Args:
            collection: The target ChromaDB collection.

        Returns:
            A StorageContext configured to write into the given collection.
        """
        vector_store = self.get_vector_store(collection)
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
