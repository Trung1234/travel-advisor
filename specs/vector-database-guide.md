# Vector Database Guide: Chroma & Azure AI Search for Travel RAG

This document provides comprehensive guidance on using Chroma (local development) and Azure AI Search (production) as vector databases for the Travel Advisor RAG system. It covers setup, configuration, document management, and best practices specific to travel domain content.

---

## Overview

The Travel Advisor RAG system uses vector databases to store and retrieve verified travel knowledge. Two providers are supported:

| Provider | Use Case | Setup Complexity | Scalability |
|----------|----------|------------------|-------------|
| **Chroma** | Local development, prototyping | Minimal | Single-machine |
| **Azure AI Search** | Production deployment | Moderate | Enterprise-scale |

Both providers support:
- **Vector search** for semantic similarity (e.g., "beach resort recommendations")
- **Keyword search** for exact terms (e.g., "SFO", "Marriott", "Hilton")
- **Hybrid search** combining both approaches
- **Metadata filtering** by document type, location, price range

---

## Part 1: Chroma (Local Development)

### Quick Start

**1. Install Chroma:**
```bash
pip install chromadb
```

**2. Start Chroma server:**
```bash
chroma run --host localhost --port 8001
```

**3. Configure in `.env`:**
```bash
RAG_ENABLED=true
RAG_PROVIDER=chroma
RAG_CHROMA_HOST=localhost
RAG_CHROMA_PORT=8001
```

### Chroma Configuration Options

```python
# backend/rag/document_store.py

class ChromaDocumentStore(DocumentStore):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8001,
        collection_name: str = "travel-docs",
        embedding_function: Optional[Callable] = None
    ):
        import chromadb
        self.client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Travel advisor knowledge base"}
        )
```

### Chroma Client Initialization

```python
# Initialize with custom embedding function
from chromadb.utils import embedding_functions

# Use nhà cung cấp dịch vụ AI embeddings (requires OPENAI_API_KEY)
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key="your-api-key",
    model_name="text-embedding-3-large"
)

# Or use the default embedding function
store = ChromaDocumentStore(
    host="localhost",
    port=8001,
    embedding_function=openai_ef
)
```

### Managing Chroma Collections

```python
from backend.rag.document_store import ChromaDocumentStore

store = ChromaDocumentStore()

# List all collections
collections = store.client.list_collections()
print(collections)

# Get collection info
collection = store.client.get_collection("travel-docs")
print(f"Document count: {collection.count()}")

# Delete a collection (careful!)
store.client.delete_collection("travel-docs")
```

### Chroma Persistence (Embedded Mode)

For local development without a server, use Chroma's embedded mode:

```python
import chromadb
from chromadb.config import Settings

# Embedded Chroma with persistent storage
client = chromadb.Client(
    Settings(
        chroma_db_impl="duckdb+parquet",
        persist_directory="./chroma_db"
    )
)

# Create or get collection
collection = client.create_collection(
    name="travel-docs",
    metadata={"persist_directory": "./chroma_db"}
)
```

---

## Part 2: Azure AI Search (Production)

### Prerequisites

1. **Azure Subscription** - Create at [Azure Portal](https://portal.azure.com)
2. **Azure AI Search Resource** - Create via Azure Portal or CLI:
   ```bash
   az search service create \
     --name my-travel-search \
     --resource-group my-resource-group \
     --sku standard \
     --location eastus
   ```
3. **API Keys** - Get from "Keys" section in Azure Portal

### Azure AI Search Configuration

**1. Configure in `.env`:**
```bash
RAG_ENABLED=true
RAG_PROVIDER=azure
RAG_AZURE_SEARCH_ENDPOINT=https://my-travel-search.search.windows.net
RAG_AZURE_SEARCH_API_KEY=your-admin-api-key
RAG_INDEX_NAME=travel-docs
```

**2. Create the search index** (first-time setup):

```python
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile
)

def create_search_index(service_endpoint: str, api_key: str, index_name: str):
    from azure.identity import DefaultAzureCredential
    
    credential = DefaultAzureCredential()
    index_client = SearchIndexClient(
        endpoint=service_endpoint,
        credential=credential
    )
    
    index = SearchIndex(
        name=index_name,
        fields=[
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(name="content", type="Edm.String"),
            SearchableField(name="title", type="Edm.String", filterable=True),
            SearchableField(name="document_type", type="Edm.String", filterable=True),
            SearchableField(name="location_hierarchy", type="Edm.String", filterable=True),
            SearchableField(name="price_range", type="Edm.String", filterable=True),
            SearchableField(name="source_url", type="Edm.String"),
            SearchableField(name="last_updated", type="Edm.DateTimeOffset", filterable=True),
            SearchableField(name="source_reliability", type="Edm.String", filterable=True),
        ],
        vector_search=VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="my-vector-profile",
                    algorithm_configuration_name="my-algorithm-config"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="my-algorithm-config",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ]
        )
    )
    
    result = index_client.create_or_update_index(index)
    print(f"Index created: {result.name}")

# Run this once to create the index
create_search_index(
    service_endpoint="https://my-travel-search.search.windows.net",
    api_key="your-admin-api-key",
    index_name="travel-docs"
)
```

### Azure AI Search Client

```python
# backend/rag/document_store.py

import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import (
    SearchedVectorQuery,
    VectorFilterMode
)

class AzureSearchDocumentStore(DocumentStore):
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        index_name: str = "travel-docs"
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.index_name = index_name
        self.search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(api_key)
        )
    
    async def store_documents(
        self,
        chunks: List[DocumentChunk],
        embeddings: List[List[float]]
    ) -> int:
        """Store documents with embeddings in Azure AI Search"""
        documents = []
        for chunk, embedding in zip(chunks, embeddings):
            doc = {
                "id": chunk.id,
                "content": chunk.content,
                "title": chunk.metadata.get("title", ""),
                "document_type": chunk.metadata.get("document_type", "general"),
                "location_hierarchy": chunk.metadata.get("location_hierarchy", ""),
                "price_range": chunk.metadata.get("price_range", ""),
                "source_url": chunk.metadata.get("source_url", ""),
                "last_updated": chunk.metadata.get("last_updated", ""),
                "source_reliability": chunk.metadata.get("source_reliability", "trusted"),
                "@search.action": "upload",
                "@search.vector": embedding
            }
            documents.append(doc)
        
        result = self.search_client.upload_documents(documents=documents)
        return len([r for r in result if r.succeeded])
    
    async def hybrid_search(
        self,
        query: str,
        embedding: List[float],
        filters: Optional[dict] = None,
        top_k: int = 10
    ) -> List[SearchResult]:
        """Perform hybrid search combining vector and keyword"""
        vector_query = SearchedVectorQuery(
            vector=embedding,
            k_nearest_neighbors=top_k,
            fields="content_vector",
            filter_mode=VectorFilterValuePreFilter
        )
        
        # Build OData filter string
        filter_str = self._build_filter_string(filters) if filters else None
        
        results = self.search_client.search(
            search_text=query,
            vector_queries=[vector_query],
            filter=filter_str,
            top=top_k,
            select=["id", "content", "title", "document_type", "source_url"]
        )
        
        return [self._map_to_search_result(r) for r in results]
```

### Azure AI Search Security Best Practices

```python
# Use Managed Identity for production
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

class AzureSearchDocumentStore(DocumentStore):
    def __init__(self, keyvault_url: str, secret_name: str):
        credential = DefaultAzureCredential()
        
        # Retrieve API key from Key Vault
        keyvault_client = SecretClient(
            vault_url=keyvault_url,
            credential=credential
        )
        api_key = keyvault_client.get_secret(secret_name).value
        
        # Get search endpoint from environment
        search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        
        super().__init__(endpoint=search_endpoint, api_key=api_key)
```

---

## Part 3: Travel Document Management

### Document Types and Structure

The RAG system supports five primary document types:

| Document Type | Description | Example Content | Chunking Strategy |
|---------------|-------------|-----------------|-------------------|
| **destination** | City/region guides, attractions | "Tokyo has excellent museums, shrines, and modern districts" | Section-based |
| **hotel** | Hotel information, amenities, policies | "Marriott Bonvoy hotels offer free breakfast and WiFi" | Per-hotel |
| **visa** | Entry requirements, documentation | "US citizens need valid passport for Japan" | Policy-based |
| **transport** | Flight, train, local transit info | "Narita Express connects airport to Tokyo in 90 minutes" | Route-based |
| **food** | Restaurant recommendations, cuisine guides | "Shinjuku has excellent ramen shops and izakaya" | Per-neighborhood |

### Document Metadata Schema

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class TravelDocumentMetadata(BaseModel):
    """Standard metadata for travel documents"""
    
    # Identification
    document_id: str
    title: str
    source_url: Optional[str] = None
    source_type: str = "official"  # official, trusted, community, ugc
    
    # Classification
    document_type: str  # destination, hotel, visa, transport, food
    location_hierarchy: Optional[str] = None  # "Japan>Tokyo"
    price_range: Optional[str] = None  # budget, mid-range, luxury
    
    # Temporal
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    last_updated: datetime = datetime.utcnow()
    
    # Access Control
    access_level: str = "public"  # public, premium, internal
    
    # Quality
    confidence_score: float = 1.0
    version: str = "1.0"
    
    # Additional
    language: str = "en"
    tags: List[str] = []
```

### Document Ingestion Pipeline

```python
from backend.rag import DocumentStore
from backend.rag.chunkers import TravelChunker
from backend.rag.embedding import get_embeddings

class DocumentIngestionPipeline:
    def __init__(
        self,
        document_store: DocumentStore,
        chunker: TravelChunker,
        embedding_model: str = "text-embedding-3-large"
    ):
        self.store = document_store
        self.chunker = chunker
        self.embedding_model = embedding_model
    
    async def ingest_document(
        self,
        content: str,
        metadata: TravelDocumentMetadata
    ) -> int:
        """Ingest a single document with chunking and embedding"""
        # 1. Chunk the document
        chunks = self.chunker.chunk(content, metadata=metadata.dict())
        
        # 2. Generate embeddings
        embeddings = await get_embeddings(
            texts=[c.content for c in chunks],
            model=self.embedding_model
        )
        
        # 3. Store in vector database
        count = await self.store.store_documents(chunks, embeddings)
        
        return count
    
    async def ingest_batch(
        self,
        documents: List[tuple[str, TravelDocumentMetadata]],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, int]:
        """Ingest multiple documents with progress tracking"""
        results = {}
        total = len(documents)
        
        for i, (content, metadata) in enumerate(documents):
            try:
                count = await self.ingest_document(content, metadata)
                results[metadata.document_id] = count
            except Exception as e:
                logger.error(f"Failed to ingest {metadata.document_id}: {e}")
                results[metadata.document_id] = 0
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return results
```

### Sample Travel Documents

```python
# Sample destination guide
DESTINATION_TOKYO = """
# Tokyo Travel Guide

Tokyo is Japan's capital and the world's most populous metropolitan area. 

## Best Time to Visit
- **Cherry Blossom (March-April)**: Peak season for hanami
- **Autumn (November)**: Beautiful foliage, comfortable weather
- **Summer (June-August)**: Hot and humid, but festivals abound
- **Winter (December-February)**: Cool, fewer crowds, New Year celebrations

## Neighborhoods
- **Shinjuku**: Business district, nightlife, observation decks
- **Shibuya**: Youth culture, shopping, famous crossing
- **Asakusa**: Traditional Tokyo, Senso-ji Temple
- **Ginza**: Upscale shopping, luxury brands
- **Harajuku**: Youth fashion, street style, crepes

## Getting Around
- **JR Yamanote Line**: Circular line connecting major areas
- **Tokyo Metro**: Extensive subway network
- **Suica/Pasmo Cards**: Contactless payment for transit

## Currency
- Japanese Yen (JPY)
- 1 USD ≈ 150 JPY (exchange rates vary)
"""

# Sample hotel information
HOTEL_MARRIOTT = """
# Marriott Bonvoy Hotels - Tokyo

## Property Overview
Marriott Bonvoy offers 50+ properties across Tokyo, from luxury to select service.

## Luxury Properties
- **The Prince Gallery Tokyo**: Kioicho, art-inspired design
- **Tokyo Marriott Hotel**: Shinagawa, near Takanawa
- **AC Hotel Tokyo**: Midtown, European style

## Mid-Range
- **Courtyard by Marriott Tokyo**: Ginza, business-friendly
- **Moxy Tokyo**: Shinjuku, boutique, youthful

## Amenities (varies by property)
- Free WiFi throughout
- Fitness centers
- On-site restaurants
- Concierge services
- Business centers

## Loyalty Program
- Points earned on stays
- Free night certificates
- Elite status benefits
- Transfer to 40+ airline partners
"""

# Sample visa information
VISA_US_JAPAN = """
# Japan Visa Requirements for US Citizens

## Visa Waiver Program
US passport holders can enter Japan for tourism or business for **up to 90 days** without a visa.

## Requirements
1. Valid US passport (6+ months remaining)
2. Return or onward ticket
3. Sufficient funds for stay
4. No employment or paid activities

## Documents to Bring
- Passport with at least 2 blank pages
- Completed entry form (provided on plane)
- Landing permission slip
- Customs declaration form

## Extension
Can extend from 90 to 180 days at local immigration office.

## Note
Visa-free entry does NOT allow:
- Employment or work
- Paid activities
- Long-term study (over 90 days)
- Married residence
"""
```

### Bulk Document Ingestion

```python
# scripts/ingest_travel_docs.py

import asyncio
from backend.rag import DocumentStore, DocumentChunk
from backend.rag.chunkers import TravelChunker
from datetime import datetime

# Pre-defined documents
DOCUMENTS = Claude-Opus

async def main():
    store = DocumentStore()
    chunker = TravelChunker()
    pipeline = DocumentIngestionPipeline(store, chunker)
    
    print("Starting document ingestion...")
    results = await pipeline.ingest_batch(DOCUMENTS)
    
    print("\nIngestion Results:")
    for doc_id, count in results.items():
        print(f"  {doc_id}: {count} chunks stored")
    
    print(f"\nTotal chunks: {sum(results.values())}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Part 4: Querying Travel Knowledge

### Basic Query

```python
from backend.rag.rag_client import get_rag_context

async def query_travel_knowledge():
    # Simple query
    context = await get_rag_context("best hotels in Tokyo with free breakfast")
    print(context.formatted_for_prompt())
    
    # With citation information
    print("\nSources:")
    for source in context.sources:
        print(f"  - {source.title} ({source.url})")
```

### Advanced Query with Filters

```python
from backend.rag.rag_client import RAGClient

client = RAGClient()

async def filtered_search():
    # Search only luxury hotels in Tokyo
    results = await client.get_context(
        query="luxury hotels with pool and spa",
        filters={
            "document_type": "hotel",
            "location_hierarchy": "Japan>Tokyo",
            "price_range": "luxury"
        }
    )
    
    return results
```

### Query Expansion for Travel Terms

```python
# Travel synonym expansion for better retrieval
TRAVEL_SYNONYMS = {
    "hotel": ["accommodation", "lodging", "inn", "resort", "stay"],
    "food": ["dining", "restaurant", "cuisine", "eatery", "eat"],
    "transport": ["transportation", "transit", "travel", "getting around", "commute"],
    "beach": ["coastal", "seaside", "shore", "ocean"],
    "budget": ["affordable", "cheap", "economical", "inexpensive", "cost-effective"],
    "luxury": ["upscale", "premium", "high-end", "five-star", "deluxe"],
    "flight": ["airline", "air travel", "plane", "airfare"],
    "tour": ["excursion", "trip", "visit", "sightseeing", "activity"],
}

def expand_travel_query(query: str) -> str:
    """Expand query with travel domain synonyms"""
    expanded = [query]
    query_lower = query.lower()
    
    for term, synonyms in TRAVEL_SYNONYMS.items():
        if term in query_lower:
            expanded.extend(synonyms)
    
    return " ".join(expanded)
```

---

## Part 5: Maintenance and Operations

### Index Health Monitoring

```python
# scripts/monitor_index.py

from backend.rag import DocumentStore

def check_index_health():
    store = DocumentStore()
    
    stats = store.get_stats()
    print(f"Document Count: {stats['document_count']}")
    print(f"Index Size: {stats['index_size_mb']} MB")
    print(f"Last Updated: {stats['last_updated']}")
    
    # Check for stale documents
    stale_threshold_days = 90
    stale_docs = store.find_stale_documents(stale_threshold_days)
    print(f"Stale Documents (>{stale_threshold_days} days): {len(stale_docs)}")
    
    return stats

def list_document_types():
    """List counts by document type"""
    store = DocumentStore()
    counts = store.get_document_type_counts()
    
    for doc_type, count in counts.items():
        print(f"  {doc_type}: {count}")
```

### Document Updates

```python
# scripts/update_document.py

from backend.rag import DocumentStore

def update_document(document_id: str, new_content: str):
    store = DocumentStore()
    
    # Get existing document
    existing = store.get_document(document_id)
    if not existing:
        print(f"Document {document_id} not found")
        return
    
    # Update content and refresh chunks/embeddings
    store.update_document(document_id, new_content)
    print(f"Updated {document_id}")

def delete_document(document_id: str):
    store = DocumentStore()
    store.delete_document(document_id)
    print(f"Deleted {document_id}")
```

### Backup and Restore

```python
# scripts/backup_index.py

import json
from backend.rag import DocumentStore

def backup_index(output_file: str):
    """Export all documents to a JSON file"""
    store = DocumentStore()
    documents = store.export_all()
    
    with open(output_file, 'w') as f:
        json.dump(documents, f, indent=2)
    
    print(f"Backed up {len(documents)} documents to {output_file}")

def restore_index(input_file: str, clear_first: bool = False):
    """Import documents from JSON file"""
    with open(input_file) as f:
        documents = json.load(f)
    
    store = DocumentStore()
    
    if clear_first:
        store.clear_all()
    
    count = store.import_documents(documents)
    print(f"Restored {count} documents")
```

---

## Part 6: Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No search results | Index empty or wrong query | Check `store.get_stats()`, verify documents ingested |
| Poor relevance | Wrong chunking strategy | Adjust `chunk_size`, review chunking logic |
| Slow queries | Large index, no caching | Implement embedding cache, use HNSW parameters |
| Authentication errors | Invalid API key or endpoint | Verify credentials, check network access |
| Memory issues | Too many embeddings in memory | Batch processing, use pagination |

### Debug Mode

```python
# Enable verbose logging for RAG operations
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("backend.rag")

# Debug query
store = DocumentStore()
results = await store.hybrid_search("hotels in Tokyo", top_k=5)

for r in results:
    logger.debug(f"Result: {r.chunk.id}, Score: {r.score}")
    logger.debug(f"Content: {r.chunk.content[:100]}...")
```

### Performance Tuning

```python
# Optimize for Chroma
CHROMA_CONFIG = {
    "hnsw:space": "cosine",  # Similarity metric
    "hnsw:construction_kwargs": {
        "ef_construction": 200,  # Higher = better recall, slower indexing
        "M": 16                   # Higher = better recall, more memory
    },
    "hnsw:search_kwargs": {
        "ef": 100                 # Higher = better recall, slower search
    }
}

# Optimize for Azure AI Search
AZURE_SEARCH_CONFIG = {
    "m": 4,                     # HNSW M parameter
    "efConstruction": 400,      # Indexing parameters
    "efSearch": 500,            # Search parameters
    "metric": "cosine"          # Similarity metric
}
```

---

## References

| Resource | URL |
|----------|-----|
| Chroma Documentation | https://docs.trychroma.com |
| Azure AI Search Documentation | https://learn.microsoft.com/azure/search |
| nhà cung cấp dịch vụ AI Embeddings |  |
| Travel Domain Chunking | See `backend/rag/chunkers.py` |
| RAG Client API | See `backend/rag/rag_client.py` |