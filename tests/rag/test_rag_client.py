import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.rag.rag_client import RAGClient, RAGClientError, get_rag_context
from backend.rag.document_store import DocumentChunk, SearchResult


@pytest.fixture
def mock_settings():
    """Mock RAG settings"""
    settings = MagicMock()
    settings.rag_settings.enabled = True
    settings.rag_settings.provider = "chroma"
    settings.rag_settings.retrieval_top_k = 5
    return settings


@pytest.fixture
def mock_search_results():
    """Mock search results from document store"""
    return Claude-Opus


@pytest.fixture
def mock_document_store(mock_search_results):
    """Mock document store"""
    store = MagicMock()
    store.hybrid_search = AsyncMock(return_value=mock_search_results)
    return store


@pytest.fixture
def rag_client(mock_document_store):
    """RAG client with mocked dependencies"""
    with patch('backend.rag.rag_client.get_document_store', return_value=mock_document_store):
        return RAGClient()


class TestRAGClient:

    def test_enabled_when_settings_configured(self, rag_client, mock_settings):
        """Test that client reports as enabled when settings are configured"""
        with patch('backend.rag.rag_client.settings', mock_settings):
            assert rag_client.enabled()

    def test_disabled_when_settings_not_configured(self, rag_client):
        """Test that client reports as disabled when settings are missing"""
        mock_settings = MagicMock()
        mock_settings.rag_settings.enabled = False

        with patch('backend.rag.rag_client.settings', mock_settings):
            assert not rag_client.enabled()

    @pytest.mark.asyncio
    async def test_get_context_success(self, rag_client, mock_search_results):
        """Test successful context retrieval"""
        with patch('backend.rag.rag_client.settings.rag_settings.enabled', True):
            context = await rag_client.get_context("Best hotels in Tokyo")

            assert context.content != ""
            assert len(context.sources) == 2
            assert "Tokyo" in context.content
            assert "Park Hyatt" in context.content

    @pytest.mark.asyncio
    async def test_get_context_empty_when_disabled(self, rag_client):
        """Test that empty context is returned when RAG is disabled"""
        with patch('backend.rag.rag_client.settings.rag_settings.enabled', False):
            context = await rag_client.get_context("Best hotels in Tokyo")

            assert context.is_empty()
            assert context.content == ""
            assert len(context.sources) == 0

    @pytest.mark.asyncio
    async def test_get_context_handles_store_error(self, rag_client):
        """Test graceful handling of document store errors"""
        mock_store = MagicMock()
        mock_store.hybrid_search = AsyncMock(side_effect=Exception("Store error"))

        with patch('backend.rag.rag_client.get_document_store', return_value=mock_store):
            with patch('backend.rag.rag_client.settings.rag_settings.enabled', True):
                with pytest.raises(RAGClientError):
                    await rag_client.get_context("Hotels in Tokyo")


class TestRAGClientFunction:

    @pytest.mark.asyncio
    async def test_get_rag_context_function(self, mock_search_results):
        """Test the module-level get_rag_context function"""
        with patch('backend.rag.rag_client.RAGClient') as mock_client_class:
            mock_client = mock_client_class.return_value
            mock_context = MagicMock()
            mock_context.content = "Mocked context"
            mock_client.get_context = AsyncMock(return_value=mock_context)

            result = await get_rag_context("Hotels in Tokyo")

            assert result.content == "Mocked context"
            mock_client.get_context.assert_called_once_with("Hotels in Tokyo")

    @pytest.mark.asyncio
    async def test_get_rag_context_raises_when_disabled(self):
        """Test that function raises error when RAG is disabled"""
        mock_settings = MagicMock()
        mock_settings.rag_settings.enabled = False

        with patch('backend.rag.rag_client.settings', mock_settings):
            with pytest.raises(RAGClientError, match="RAG is not enabled"):
                await get_rag_context("Hotels in Tokyo")


class TestRAGContext:

    def test_format_for_prompt(self, mock_search_results):
        """Test RAG context formatting for prompt injection"""
        from backend.rag.rag_client import RAGContext

        context = RAGContext.from_results(mock_search_results)
        formatted = context.formatted_for_prompt()

        assert "[VERIFIED TRAVEL KNOWLEDGE]" in formatted
        assert "Tokyo has many excellent hotels" in formatted
        assert "Best time to visit Tokyo" in formatted
        assert "Sources:" in formatted
        assert "https://example.com/tokyo-hotels" in formatted

    def test_empty_context(self):
        """Test empty RAG context"""
        from backend.rag.rag_client import RAGContext

        context = RAGContext.empty()

        assert context.is_empty()
        assert context.content == ""
        assert len(context.sources) == 0
        assert context.formatted_for_prompt() == ""