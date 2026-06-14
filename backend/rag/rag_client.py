"""
RAG client following the serpapi_client.py pattern for consistency.
"""
from functools import lru_cache
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from ..config import settings
from .document_store import DocumentStore, AzureAISearchStore, ChromaStore
from .retriever import HybridRetriever, CachedRetriever

logger = logging.getLogger("backend.rag.rag_client")


class RAGClientError(RuntimeError):
    """Raised when RAG operations fail."""
    pass


@dataclass
class RAGSource:
    """Source information for citations."""
    title: str
    url: Optional[str]
    document_type: str
    relevance: float
    chunk_id: str


@dataclass
class RAGContext:
    """Formatted context with source citations."""
    content: str
    sources: List[RAGSource]
    total_results: int

    @classmethod
    def empty(cls) -> "RAGContext":
        """Return empty context for graceful fallbacks."""
        return cls(content="", sources=[], total_results=0)

    def formatted_for_prompt(self) -> str:
        """Format context for injection into chat prompt."""
        if not self.content:
            return ""

        # Format sources for citation
        sources_text = ""
        if self.sources:
            sources_text = "\n\nSources:\n"
            for i, source in enumerate(self.sources, 1):
                url_part = f" ({source.url})" if source.url else ""
                sources_text += f"[{i}] {source.title}{url_part}\n"

        return f"{self.content}{sources_text}"

    def has_content(self) -> bool:
        """Check if context contains useful information."""
        return bool(self.content.strip())


class RAGClient:
    """
    RAG client that follows the same pattern as serpapi_client.py.

    Provides document retrieval with hybrid search and source citations.
    """

    def __init__(self) -> None:
        self._retriever: Optional[CachedRetriever] = None
        self._document_store: Optional[DocumentStore] = None

    def enabled(self) -> bool:
        """Check if RAG is properly configured and enabled."""
        if not settings.rag_settings.enabled:
            return False

        # Check provider-specific configuration
        if settings.rag_settings.provider == "azure":
            return (
                settings.rag_settings.azure_search_endpoint and
                settings.rag_settings.azure_search_api_key
            )
        elif settings.rag_settings.provider == "chroma":
            return True  # Chroma works locally without external config

        return False

    @property
    def retriever(self) -> CachedRetriever:
        """Lazy-initialize retriever."""
        if self._retriever is None:
            self._retriever = self._create_retriever()
        return self._retriever

    @property
    def document_store(self) -> DocumentStore:
        """Lazy-initialize document store."""
        if self._document_store is None:
            self._document_store = self._create_document_store()
        return self._document_store

    def _create_document_store(self) -> DocumentStore:
        """Create document store based on configuration."""
        try:
            if settings.rag_settings.provider == "azure":
                return AzureAISearchStore(
                    endpoint=settings.rag_settings.azure_search_endpoint,
                    api_key=settings.rag_settings.azure_search_api_key,
                    index_name=settings.rag_settings.index_name
                )
            elif settings.rag_settings.provider == "chroma":
                return ChromaStore(
                    persist_directory="./chroma_db",
                    collection_name=settings.rag_settings.index_name
                )
            else:
                raise RAGClientError(f"Unsupported provider: {settings.rag_settings.provider}")

        except Exception as e:
            logger.error(f"Failed to create document store: {e}")
            raise RAGClientError(f"Document store initialization failed: {e}")

    def _create_retriever(self) -> CachedRetriever:
        """Create retriever with caching."""
        base_retriever = HybridRetriever(
            document_store=self.document_store,
            vector_weight=0.7,
            keyword_weight=0.3
        )

        return CachedRetriever(
            retriever=base_retriever,
            cache_ttl=3600  # 1 hour cache
        )

    async def get_context(
        self,
        query: str,
        document_types: Optional[List[str]] = None,
        user_role: str = "public"
    ) -> RAGContext:
        """
        Get RAG context for a travel query.

        Args:
            query: User's travel query
            document_types: Optional filter for document types
            user_role: User role for access control (future feature)

        Returns:
            RAGContext with formatted content and sources
        """
        if not self.enabled():
            logger.debug("RAG is disabled or not configured")
            return RAGContext.empty()

        try:
            # Build filters
            filters = {}
            if document_types:
                filters["document_type"] = document_types

            # Retrieve relevant documents
            results = await self.retriever.search(
                query=query,
                filters=filters,
                top_k=settings.rag_settings.retrieval_top_k
            )

            if not results:
                logger.info(f"No RAG results for query: {query[:50]}...")
                return RAGContext.empty()

            # Format context with sources
            content_parts = []
            sources = []

            for i, result in enumerate(results):
                # Add content with reference number
                content_parts.append(f"[{i+1}] {result.content.strip()}")

                # Create source for citation
                metadata = result.metadata
                source = RAGSource(
                    title=metadata.get("title", f"Travel Document {i+1}"),
                    url=metadata.get("source_url"),
                    document_type=metadata.get("document_type", "general"),
                    relevance=result.combined_score,
                    chunk_id=result.id
                )
                sources.append(source)

            # Combine content
            formatted_content = "\n\n".join(content_parts)

            logger.info(f"RAG context for '{query[:50]}...': {len(results)} chunks")

            return RAGContext(
                content=formatted_content,
                sources=sources,
                total_results=len(results)
            )

        except Exception as e:
            logger.error(f"RAG context retrieval failed for '{query}': {e}")
            return RAGContext.empty()

    def clear_cache(self):
        """Clear retrieval cache."""
        if self._retriever:
            self._retriever.clear_cache()
            logger.info("RAG cache cleared")


@lru_cache
def get_rag_client() -> RAGClient:
    """
    Get cached RAG client instance.

    Follows the same pattern as get_client() in agent.py.
    """
    if not settings.rag_settings.enabled:
        raise RAGClientError("RAG is not enabled")

    return RAGClient()


async def get_rag_context(
    query: str,
    document_types: Optional[List[str]] = None,
    user_role: str = "public"
) -> RAGContext:
    """
    Public function to get RAG context.

    Follows the same pattern as get_serpapi_results() in serpapi_client.py.

    Args:
        query: Travel query
        document_types: Optional document type filters
        user_role: User role for access control

    Returns:
        RAGContext with content and citations

    Raises:
        RAGClientError: If RAG is not configured or fails
    """
    try:
        client = get_rag_client()
        return await client.get_context(query, document_types, user_role)
    except RAGClientError:
        # Return empty context for graceful degradation
        logger.warning("RAG client error, returning empty context")
        return RAGContext.empty()


def format_rag_context_for_agent(context: RAGContext) -> str:
    """
    Format RAG context for agent prompt injection.

    This follows the same pattern as _format_serpapi_context() in agent.py.
    """
    if not context.has_content():
        return ""

    lines = ["Travel knowledge base context:"]

    # Add content with source markers
    for i, source in enumerate(context.sources, 1):
        lines.append(f"[{i}] {source.title} ({source.document_type})")

    lines.append("")  # Blank line
    lines.append(context.content)

    return "\n".join(lines)


# Health check function for RAG system
def rag_health_check() -> Dict[str, Any]:
    """
    Check RAG system health status.

    Returns:
        Dict with health information
    """
    status = {
        "enabled": settings.rag_settings.enabled,
        "provider": settings.rag_settings.provider,
        "configured": False,
        "error": None
    }

    if not settings.rag_settings.enabled:
        status["error"] = "RAG is disabled"
        return status

    try:
        client = get_rag_client()
        status["configured"] = client.enabled()

        if not status["configured"]:
            status["error"] = f"Provider '{settings.rag_settings.provider}' not properly configured"

    except Exception as e:
        status["error"] = str(e)

    return status