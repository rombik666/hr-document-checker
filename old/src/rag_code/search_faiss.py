import argparse

from rag_code.config import INDEX_DIR, settings
from rag_code.retriever import FaissRetriever

INDEX_FILE_NAME = "faiss.index"
METADATA_FILE_NAME = "chunks_metadata.json"

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search relevant chunks in a FAISS index"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="User query for semantic search",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=settings.top_k,
        help="Number of chunks to return"
    )

    return parser

def print_results(results: list[dict]) -> None:
    if not results:
        print("No results found")
        return
    
    for item in results:
        print("=" * 80)
        print(f'Rank: {item["rank"]}')
        print(f'Score: {item["score"]:.4f}')
        print(f'File: {item["file_name"]}')
        print(f'Source: {item["source"]}')
        print(f'Chunk ID: {item["chunk_id"]}')
        print(f'Chars: {item["start_char"]}-{item["end_char"]}')
        print("Text:")
        print(item["text"])
    print("=" * 80)

def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    retriever = FaissRetriever(
        embedding_model_name=settings.embedding_model_name,
        index_path=INDEX_DIR / INDEX_FILE_NAME,
        metadata_path=INDEX_DIR / METADATA_FILE_NAME,
        top_k=args.top_k,
    )

    results = retriever.retrieve(
        query=args.query,
        top_k=args.top_k,
    )

    print_results(results)

if __name__ == "__main__":
    main()