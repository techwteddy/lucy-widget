import pytest
from unittest.mock import patch, MagicMock, AsyncMock


class TestChunker:
    def test_basic_chunking(self):
        from api.services.chunker import chunk_text
        text = "Hello world. " * 50  # ~650 chars
        chunks = chunk_text(text, chunk_size=100, overlap=20)
        assert len(chunks) > 1
        assert all(isinstance(c, str) for c in chunks)
        assert all(c.strip() for c in chunks)

    def test_short_text_single_chunk(self):
        from api.services.chunker import chunk_text
        text = "Short text."
        chunks = chunk_text(text, chunk_size=400, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunks_contain_original_content(self):
        from api.services.chunker import chunk_text
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        chunks = chunk_text(text, chunk_size=40, overlap=10)
        combined = " ".join(chunks)
        # Key words should appear somewhere
        assert "First" in combined
        assert "Fourth" in combined

    def test_empty_text(self):
        from api.services.chunker import chunk_text
        chunks = chunk_text("", chunk_size=400, overlap=50)
        assert chunks == []

    def test_chunk_size_respected(self):
        from api.services.chunker import chunk_text
        text = "Word. " * 200  # ~1200 chars
        chunks = chunk_text(text, chunk_size=200, overlap=20)
        # Most chunks should be close to chunk_size
        for chunk in chunks[:-1]:  # last chunk can be short
            assert len(chunk) <= 300  # allow some overage from sentence boundaries

    def test_returns_list_of_strings(self):
        from api.services.chunker import chunk_text
        result = chunk_text("Some text here.")
        assert isinstance(result, list)


class TestEmbedder:
    @pytest.mark.asyncio
    async def test_embed_returns_list_of_floats(self):
        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1] * 768
        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch("api.services.embedder._get_client", return_value=mock_client):
            from api.services.embedder import embed
            result = await embed("test text")
            assert isinstance(result, list)
            assert len(result) == 768
            assert all(isinstance(v, float) for v in result)

    @pytest.mark.asyncio
    async def test_embed_batch_returns_correct_count(self):
        mock_client = MagicMock()
        mock_embeddings = [MagicMock() for _ in range(3)]
        for i, e in enumerate(mock_embeddings):
            e.values = [float(i) / 10] * 768
        mock_result = MagicMock()
        mock_result.embeddings = mock_embeddings
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch("api.services.embedder._get_client", return_value=mock_client):
            from api.services.embedder import embed_batch
            result = await embed_batch(["a", "b", "c"])
            assert len(result) == 3
            assert all(len(v) == 768 for v in result)

    @pytest.mark.asyncio
    async def test_embed_truncates_long_text(self):
        mock_client = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.values = [0.1] * 768
        mock_result = MagicMock()
        mock_result.embeddings = [mock_embedding]
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_result)

        with patch("api.services.embedder._get_client", return_value=mock_client):
            from api.services.embedder import embed, MAX_CHARS
            long_text = "x" * (MAX_CHARS + 1000)
            await embed(long_text)

            call_kwargs = mock_client.aio.models.embed_content.call_args
            passed_contents = call_kwargs.kwargs.get("contents") or call_kwargs[1].get("contents") or call_kwargs[0][1]
            assert len(passed_contents[0]) <= MAX_CHARS
