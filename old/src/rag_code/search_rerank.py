import argparse

from rag_code.config import INDEX_DIR, settings
from rag_code.retriever import FaissRetriever
from rag_code.reranker import  CrossEncoderReranker

INDEX_FILE_NAME = "faiss.index"
METADATA_FILE_NAME = "chunks_metadata.json"

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Retrieve chunks with FAISS and rerank them with a CrossEncoder"
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="User query for retrieval and reranking",
    )
    parser.add_argument(
        "--faiss-top-k",
        type=int,
        default=settings.top_k,
        help="Number of chunks to retrieve from FAISS before reranking",
    )
    parser.add_argument(
        "--rerank-top-n",
        type=int,
        default=settings.rerank_top_n,
        help="Number of chunks to keep after reranking",
    )
    return parser

def print_faiss_results(results: list[dict]) -> None:
    print("\nFAISS results:")

    if not results:
        print("No FAISS results found.")
        return
    
    for item in results:
        print("-" * 80)
        print(f'FAISS rank: {item["rank"]}')
        print(f'FAISS score: {item["score"]:.4f}')
        print(f'File: {item["file_name"]}')
        print(f'Chunk ID: {item["chunk_id"]}')
        print(item["text"])

def print_reranked_results(results: list[dict]) -> None:
    print("\nReranked results:")

    if not results:
        print("No reranked results found.")
        return
    
    for item in results:
        print("=" * 80)
        print(f'Rerank rank: {item["rerank_rank"]}')
        print(f'Rerank score: {item["rerank_score"]:.4f}')
        print(f'Original FAISS rank: {item["rank"]}')
        print(f'Original FAISS score: {item["score"]:.4f}')
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
        top_k=args.faiss_top_k,
    )

    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model_name,
    )

    faiss_results = retriever.retrieve(
        query=args.query,
        top_k=args.faiss_top_k,
    )

    reranked_results = reranker.rerank(
        query=args.query,
        candidates=faiss_results,
        top_n=args.rerank_top_n,
    )

    print_faiss_results(faiss_results)
    print_reranked_results(reranked_results)

if __name__ == "__main__":
    main()