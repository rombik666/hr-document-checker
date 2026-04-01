from rag_code.chunker import chunk_documents
from rag_code.config import INDEX_DIR, RAW_DATA_DIR, settings
from rag_code.embedder import SentenceTransformerEmbedder
from rag_code.loader import load_documents
from rag_code.vector_store import FaissVectorStore

from pathlib import Path

INDEX_FILE_NAME = "faiss.index"
METADATA_FILE_NAME = "chunks_metadata.json"

def main() -> None:
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    documents = load_documents(RAW_DATA_DIR)

    if not documents:
        raise ValueError(f"No supported documents found in {RAW_DATA_DIR}. Add .txt or .md files first.")
    
    chunks = chunk_documents(
        documents=documents,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    if not chunks:
        raise ValueError("No chunks were created from the loaded documents")
    
    texts = [chunks["text"] for chunk in chunks]
    embedder = SentenceTransformerEmbedder(settings.embedding_model_name)
    embeddings = embedder.encode_texts(texts)

    vector_store = FaissVectorStore(dimension=embeddings.shape[1])
    vector_store.add(embeddings=embeddings, metadata=chunks)

    vector_store.save(
        index_path=INDEX_DIR / INDEX_FILE_NAME,
        metadata_path=INDEX_DIR / METADATA_FILE_NAME,
    )

    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Embedding dimension: {embeddings.shape[1]}")
    print(f"Index saved to: {INDEX_DIR / INDEX_FILE_NAME}")
    print(f"Metadata saved to: {INDEX_DIR / METADATA_FILE_NAME}")

if __name__ == "__main__":
    main()