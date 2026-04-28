import argparse

from rag_code.config import INDEX_DIR, settings
from rag_code.generator import OpenAIChatGenerator
from rag_code.reranker import CrossEncoderReranker
from rag_code.retriever import FaissRetriever

INDEX_FILE_NAME = "faiss.index"
METADATA_FILE_NAME = "chunks_metadata.json"

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        "Run the full RAG pipeline: retrieve, rerank, and generate an answer"
    )

    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="User question for the RAG pipeline",
    )
    parser.add_argument(
        "--faiss-top-k",
        type=int,
        default=settings.top_k,
        help="Number of chunks to retrieve from FAISS",
    )
    parser.add_argument(
        "--rerank-top-n",
        type=int,
        default=settings.rerank_top_n,
        help="Number of reranked chunks to pass to the LLM",
    )
    parser.add_argument(
        "--show-context",
        action="store_true",
        help="Print reranked chunks before the final answer",
    )
    return parser

def print_reranker_chunks(chunks: list[dict]) -> None:
    print("\nReranked context:")

    if not chunks:
        print("No reranked chunks found.")
        return
    
    for item in chunks:
        print("=" * 80)
        print(f'Rerank rank: {item["rerank_rank"]}')
        print(f'Rerank score: {item["rerank_score"]:.4f}')
        print(f'Original FAISS rank: {item["rank"]}')
        print(f'File: {item["file_name"]}')
        print(f'Chunk ID: {item["chunk_id"]}')
        print("Text:")
        print(item["text"])
    print("=" * 80)

def print_final_answer(result: dict) -> None:
    print("\nFinal answer:")
    print("=" * 80)
    print(result["answer"])
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
        model_name=settings.reranker_model_name
    )

    generator = OpenAIChatGenerator(
        model_name=settings.llm_model_name,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    faiss_results = retriever.retrieve(
        query=args.query,
        top_k=args.faiss_top_k,
    )

    reranked_chunks = reranker.rerank(
        query=args.query,
        candidates=faiss_results,
        top_n=args.rerank_top_n,
    )

    if not reranked_chunks:
        print("No relevant chunks were found for generation.")
        return
    
    if args.show_context:
        print_reranker_chunks(reranked_chunks)

    generation_results = generator.generate_answer(
        query=args.query,
        chunks=reranked_chunks,
    )

    print_final_answer(generation_results)

if __name__ == "__main__":
    main()