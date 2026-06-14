"""
Abstract document store for RAG with Azure AI Search and Chroma implementations.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, List, Optional
import logging

logger = logging.getLogger("backend.rag.document_store")


@dataclass
class DocumentChunk:
    """A chunk of a document with content and metadata."""
    id: str
    content: str
    metadata: dict[str, Any]
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """A search result from the document store."""
    chunk: DocumentChunk
    score: float
    vector_score: float = 0.0
    keyword_score: float = 0.0


class DocumentStore(ABC):
    """Abstract base class for document stores."""

    @abstractmethod
    async def store_documents(self, chunks: List[DocumentChunk]) -> int:
        """Store document chunks and return count stored."""
        ...

    @abstractmethod
    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        filters: Optional[dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Perform hybrid search (vector + keyword) and return results."""
        ...

    @abstractmethod
    async def delete_documents(self, doc_ids: List[str]) -> int:
        """Delete documents by their IDs and return count deleted."""
        ...

    @abstractmethod
    async def clear_all(self) -> int:
        """Clear all documents and return count deleted."""
        ...


class ChromaDocumentStore(DocumentStore):
    """ChromaDB-based document store for local development."""

    def __init__(
        self,
        collection_name: str = "travel-docs",
        persist_directory: str = "./chroma_db"
    ):
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            logger.error("ChromaDB not installed. Run: pip install chromadb")
            raise

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Travel advisor document store"}
        )
        logger.info(f"Initialized ChromaDB store with collection: {collection_name}")

    async def store_documents(self, chunks: List[DocumentChunk]) -> int:
        """Store document chunks in ChromaDB."""
        if not chunks:
            return 0

        ids = [chunk.id for chunk in chunks]
        contents = [chunk.content for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        embeddings = [chunk.embedding for chunk in chunks if chunk.embedding is not None]

        # Store embeddings and content
        self.collection.add(
            ids=ids,
            documents=contents,
            metadatas=metadadas,
            embeddings=embeddings if embeddings else None
        )

        logger.info(f"Stored {len(chunks)} document chunks")
        return len(chunks)

    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        filters: Optional[dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Perform hybrid search using Chroma's built-in hybrid search."""
        where = filters if filters else {}

        # ChromaDB supports hybrid search via query_texts and include
        results = self.collection.query(
            query_texts=[query],
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )

        search_results = []
        for i, (doc_id, doc_content, doc_meta, distance) in enumerate(zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        )):
            # Convert distance to similarity score (Chroma uses distance)
            score = 1.0 - (distance if distance else 0.5)
            search_results.append(SearchResult(
                chunk=DocumentChunk(
                    id=doc_id,
                    content=doc_content,
                    metadata=doc_meta or {}
                ),
                score=score,
                vector_score=score,
                keyword_score=score  # Chroma combines both
            ))

        return search_results

    async def delete_documents(self, doc_ids: List[str]) -> int:
        """Delete documents from ChromaDB."""
        if not doc_ids:
            return 0

        self.collection.delete(ids=doc_ids)
        logger.info(f"Deleted {len(doc_ids)} documents")
        return len(doc_ids)

    async def clear_all(self) -> int:
        """Clear all documents from the collection."""
        count = self.collection.count()
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"description": "Travel advisor document store"}
        )
        logger.info(f"Cleared {count} documents")
        return count


class AzureAISearchStore(DocumentStore):
    """Azure AI Search-based document store for production."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        index_name: str = "travel-docs"
    ):
        try:
            from azure.search.documents import SearchClient
            from azure.core.credentials import AzureKeyCredential
        except ImportError:
            logger.error("azure-search-documents not installed. Run: pip install azure-search-documents")
            raise

        self.endpoint = endpoint
        self.api_key = api_key
        self.index_name = index_name
        self.client = SearchClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key),
            index_name=index_name
        )
        logger.info(f"Initialized Azure AI Search store: {endpoint}")

    async def store_documents(self, chunks: List[DocumentChunk]) -> int:
        """Store document chunks in Azure AI Search."""
        if not chunks:
            return 0

        from azure.search.documents.models import IndexingBatch, SearchIndexableDocument

        documents = []
        for chunk in chunks:
            doc = {
                "id": chunk.id,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "embedding": chunk.embedding
            }
            documents.append(SearchIndexableDocument(**doc))

        batch = IndexingBatch(operations=[
            {
                "actionType": "upload",
                "document": doc
            }
            for doc in documents
        ])

        self.client.index_batch(batch=batch)
        logger.info(f"Stored {len(chunks)} document chunks in Azure Search")
        return len(chunks)

    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        filters: Optional[dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Perform hybrid search using Azure AI Search."""
        from azure.search.documents.models import VectorQuery, VectorizedQuery

        # Create vector query
        vector_query = VectorizedQuery(
            vector=embedding,
            fields=["embedding"],
            k_nearest_neighbors=top_k
        )

        # Build filter string from dict
        filter_str = None
        if filters:
            filter_parts = []
            for key, value in filters.items():
                if isinstance(value, str):
                    filter_parts.append(f"{key} eq '{value}'")
                else:
                    filter_parts.append(f"{key} eq {value}")
            filter_str = " and ".join(filter_parts)

        # Execute search
        results = self.client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=filter_str,
            top=top_k,
            include_total_count=True
        )

        search_results = []
        for result in results:
            # Azure returns @search.score as relevance score
            score = result.get("@search.score", 0.5)
            search_results.append(SearchResult(
                chunk=DocumentChunk(
                    id=result["id"],
                    content=result["content"],
                    metadata=result.get("metadata", {})
                ),
                score=score,
                vector_score=score,
                keyword_score=score  # Azure handles hybrid scoring internally
            ))

        return search_results

    async def delete_documents(self, doc_ids: List[str]) -> int:
        """Delete documents from Azure AI Search."""
        if not doc_ids:
            return 0

        from azure.search.documents.models import IndexingBatch, SearchIndexableDocument

        batch = IndexingBatch(operations=[
            {
                "actionType": "delete",
                "document": {"id": doc_id}
            }
            for doc_id in doc_ids
        ])

        self.client.index_batch(batch=batch)
        logger.info(f"Deleted {len(doc_ids)} documents from Azure Search")
        return len(doc_ids)

    async def clear_all(self) -> int:
        """Clear all documents from the index."""
        # First get all document IDs
        results = self.client.search(search_text="*", select=["id"], top=1000)
        doc_ids = [result["id"] for result in results]

        if doc_ids:
            await self.delete_documents(doc_ids)

        logger.info(f"Cleared all documents from Azure Search")
        return len(doc_ids)


def create_document_store(
    provider: str = "azure",
    **kwargs
) -> DocumentStore:
    """Factory function to create document store based on provider."""
    if provider == "chroma":
        return ChromaDocumentStore(
            collection_name=kwargs.get("index_name", "travel-docs"),
            persist_directory=kwargs.get("persist_directory", "./chroma_db")
        )
    elif provider == "azure":
        return AzureAISearchStore(
            endpoint=kwargs["azure_search_endpoint"],
            api_key=kwargs["azure_search_api_key"],
            index_name=kwargs.get("index_name", "travel-docs")
        )
    else:
        raise ValueError(f"Unknown document store provider: {provider}")