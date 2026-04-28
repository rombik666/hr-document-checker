from rag_code.chunker import chunk_documents
from rag_code.config import INDEX_DIR, RAW_DATA_DIR, settings
from rag_code.embedder import SentenceTransformerEmbedder
from rag_code.loader import load_documents
from rag_code.vector_store import FaissVectorStore
from rag_code.logger import get_logger, setup_logging

from pathlib import Path

INDEX_FILE_NAME = "faiss.index"
METADATA_FILE_NAME = "chunks_metadata.json"

logger = get_logger(__name__)

def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Starting index build")

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    documents = load_documents(RAW_DATA_DIR)
    logger.info("Loaded %d documents from %s", len(documents), RAW_DATA_DIR)

    if not documents:
        logger.error("No supported documents found in %s", RAW_DATA_DIR)
        raise ValueError(f"No supported documents found in {RAW_DATA_DIR}. Add .txt or .md files first.")
    
    chunks = chunk_documents(
        documents=documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    logger.info("Created %d chunks", len(chunks))

    if not chunks:
        logger.error("No chunks were created from the loaded documents")
        raise ValueError("No chunks were created from the loaded documents")
    
    texts = [chunk["text"] for chunk in chunks]
    embedder = SentenceTransformerEmbedder(settings.embedding_model_name)
    logger.info("Encoding chunks with model %s", settings.embedding_model_name)
    embeddings = embedder.encode_texts(texts)

    vector_store = FaissVectorStore(dimension=embeddings.shape[1])
    vector_store.add(embeddings=embeddings, metadata=chunks)

    vector_store.save(
        index_path=INDEX_DIR / INDEX_FILE_NAME,
        metadata_path=INDEX_DIR / METADATA_FILE_NAME,
    )

    logger.info("Index build completed successfully")
    logger.info("Documents loaded: %d", len(documents))
    logger.info("Chunks created: %d", len(chunks))
    logger.info("Embedding dimension: %d", embeddings.shape[1])
    logger.info("Index saved to: %s", INDEX_DIR / INDEX_FILE_NAME)
    logger.info("Metadata saved to: %s", INDEX_DIR / METADATA_FILE_NAME)
    
    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Index saved to: {INDEX_DIR / INDEX_FILE_NAME}")
    print(f"Metadata saved to: {INDEX_DIR / METADATA_FILE_NAME}")

if __name__ == "__main__":
    main()