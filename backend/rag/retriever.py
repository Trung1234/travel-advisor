"""
Hybrid retriever combining vector search with keyword matching.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re
import logging

from .config import settings
from .document_store import DocumentStore, SearchResult

logger = logging.getLogger("backend.rag.retriever")


@dataclass
class HybridSearchResult:
    """Combined search result with vector and keyword scores."""
    id: str
    content: str
    metadata: Dict[str, Any]
    vector_score: float
    keyword_score: float
    combined_score: float
    source: str


class KeywordExtractor:
    """Extract and normalize travel-specific keywords from queries."""

    def __init__(self):
        # Common travel term variations
        self.synonyms = {
            "hotel": ["accommodation", "lodging", "stay", "inn", "resort"],
            "destination": ["place", "location", "city", "country", "area"],
            "food": ["dining", "restaurant", "cuisine", "eating", "meal"],
            "transport": ["transportation", "getting around", "travel to", "how to get"],
            "flight": ["airline", "airport", "fly", "plane"],
            "weather": ["climate", "temperature", "forecast", "season"],
            "price": ["cost", "budget", "expensive", "cheap", "affordable"],
            "activity": ["attraction", "thing to do", "sightseeing", "tour"]
        }

        # Airport code pattern
        self.airport_pattern = re.compile(r'\b[A-Z]{3}\b')

        # Hotel brand pattern
        self.hotel_brands = [
            "marriott", "hilton", "hyatt", "ihg", "intercontinental",
            "sheraton", "westin", "radisson", "accor", "best western",
            "doubletree", "conrad", "renaissance", "autograph"
        ]

    def extract(self, query: str) -> List[str]:
        """Extract key terms from a travel query."""
        query_lower = query.lower()
        terms = set()

        # Add original words
        words = re.findall(r'\b[a-z]+\b', query_lower)
        terms.update(words)

        # Add synonyms
        for word in words:
            if word in self.synonyms:
                terms.update(self.synonyms[word])

        # Extract airport codes
        airport_codes = self.airport_pattern.findall(query)
        terms.update([code.lower() for code in airport_codes])

        # Detect hotel brands
        for brand in self.hotel_brands:
            if brand in query_lower:
                terms.add(brand)

        return list(terms)

    def expand_query(self, query: str) -> List[str]:
        """Expand query with travel-specific variations."""
        terms = self.extract(query)
        expanded = set(terms)

        # Add common combinations
        if "hotel" in terms or "accommodation" in terms:
            expanded.add("where to stay")
            expanded.add("hotel recommendation")

        if "food" in terms or "restaurant" in terms:
            expanded.add("dining options")
            expanded.add("local cuisine")

        if "destination" in terms:
            expanded.add("travel guide")
            expanded.add("tourist information")

        return list(expanded)


class HybridRetriever:
    """Retriever combining semantic (vector) and keyword search."""

    def __init__(
        self,
        document_store: DocumentStore,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        embedding_model: Optional[str] = None
    ):
        self.document_store = document_store
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight
        self.embedding_model = embedding_model or settings.rag_settings.provider
        self.keyword_extractor = KeywordExtractor()

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[HybridSearchResult]:
        """
        Perform hybrid search combining vector and keyword similarity.

        Args:
            query: Search query
            filters: Optional metadata filters (e.g., {"document_type": "destination"})
            top_k: Number of results to return

        Returns:
            List of combined search results sorted by combined score
        """
        try:
            # Extract keywords for expansion
            expanded_terms = self.keyword_extractor.expand_query(query)

            # Get results from document store
            results = await self.document_store.hybrid_search(
                query=query,
                filters=filters,
                top_k=top_k * 2  # Get more results for merging
            )

            if not results:
                logger.info("No results from document store")
                return []

            # Calculate keyword scores for each result
            for result in results:
                result.keyword_score = self._calculate_keyword_score(
                    result.chunk.content, expanded_terms
                )

            # Merge and deduplicate results
            merged = self._merge_results(results, top_k)

            logger.info(f"Hybrid search for '{query[:50]}...': {len(merged)} results")
            return merged

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            return []

    def _calculate_keyword_score(self, content: str, terms: List[str]) -> float:
        """Calculate keyword match score based on term frequency."""
        if not terms:
            return 0.0

        content_lower = content.lower()
        matches = 0

        for term in terms:
            # Exact match
            if term in content_lower:
                matches += 1
            # Partial match (word contains term)
            elif any(term in word for word in content_lower.split()):
                matches += 0.5

        return matches / len(terms)

    def _merge_results(
        self,
        results: List[SearchResult],
        top_k: int
    ) -> List[HybridSearchResult]:
        """Merge vector and keyword results with deduplication."""
        # Normalize scores
        max_vector = max((r.vector_score for r in results), default=1)
        max_keyword = max((r.keyword_score for r in results), default=1)

        merged_map: Dict[str, HybridSearchResult] = {}

        for result in results:
            # Skip results with very low scores
            if result.vector_score < 0.1 and result.keyword_score < 0.1:
                continue

            # Calculate combined score
            vector_norm = result.vector_score / max_vector if max_vector > 0 else 0
            keyword_norm = result.keyword_score / max_keyword if max_keyword > 0 else 0
            combined = (
                self.vector_weight * vector_norm +
                self.keyword_weight * keyword_norm
            )

            chunk_id = result.chunk.id

            # If we've seen this chunk, merge scores
            if chunk_id in merged_map:
                existing = merged_map[chunk_id]
                existing.combined_score = max(existing.combined_score, combined)
                existing.vector_score = max(existing.vector_score, result.vector_score)
                existing.keyword_score = max(existing.keyword_score, result.keyword_score)
            else:
                merged_map[chunk_id] = HybridSearchResult(
                    id=chunk_id,
                    content=result.chunk.content,
                    metadata=result.chunk.metadata,
                    vector_score=result.vector_score,
                    keyword_score=result.keyword_score,
                    combined_score=combined,
                    source=result.source
                )

        # Sort by combined score and return top_k
        sorted_results = sorted(
            merged_map.values(),
            key=lambda x: x.combined_score,
            reverse=True
        )

        return sorted_results[:top_k]


class CachedRetriever:
    """Retriever with Redis-based caching for embeddings and results."""

    def __init__(
        self,
        retriever: HybridRetriever,
        cache_ttl: int = 3600  # 1 hour default
    ):
        self.retriever = retriever
        self.cache_ttl = cache_ttl
        self._embedding_cache: Dict[str, List[float]] = {}

    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = 10
    ) -> List[HybridSearchResult]:
        """Search with caching for repeated queries."""
        cache_key = self._make_cache_key(query, filters)

        # Check cache
        # Note: In production, this would use Redis
        # For now, we use simple in-memory cache
        if hasattr(self, '_result_cache'):
            if cache_key in self._result_cache:
                import time
                cached_time, results = self._result_cache[cache_key]
                if time.time() - cached_time < self.cache_ttl:
                    logger.debug(f"Cache hit for query: {query[:50]}...")
                    return results

        # Perform search
        results = await self.retriever.search(query, filters, top_k)

        # Cache results
        if not hasattr(self, '_result_cache'):
            self._result_cache = {}

        import time
        self._result_cache[cache_key] = (time.time(), results)

        return results

    def _make_cache_key(
        self,
        query: str,
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate a cache key for a query."""
        import hashlib
        key_parts = [query]

        if filters:
            for k, v in sorted(filters.items()):
                key_parts.append(f"{k}={v}")

        key_str = "".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    def clear_cache(self):
        """Clear the result cache."""
        self._result_cache = {}
        self._embedding_cache = {}
        logger.info("Retriever cache cleared")