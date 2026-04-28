from app.rag.chunker import TextChunker
from app.schemas.rag import RagSource


def test_text_chunker_splits_source_into_chunks() -> None:
    source = RagSource(
        source_id="source-1",
        title="rules",
        path="rules.md",
        content="Python backend developer. " * 100,
    )

    chunker = TextChunker(
        chunk_size_chars=200,
        overlap_chars=20,
    )

    chunks = chunker.chunk_sources([source])

    assert len(chunks) > 1
    assert chunks[0].source_id == "source-1"
    assert chunks[0].title == "rules"
    assert chunks[0].text