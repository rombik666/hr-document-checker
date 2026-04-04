import csv
import json
from pathlib import Path
from statistics import mean

from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from ragas.llms import llm_factory

try:
    from ragas.embeddings import HuggingFaceEmbeddings
except ImportError:
    from ragas.embeddings import HuggingfaceEmbeddings as HuggingFaceEmbeddings

try:
    from ragas.metrics.collections import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
    )
except ImportError:
    from ragas.metrics import (
        Faithfulness,
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
    )

from rag_code.config import BASE_DIR, INDEX_DIR, settings
from rag_code.generator import OpenAIChatGenerator
from rag_code.reranker import CrossEncoderReranker
from rag_code.retriever import FaissRetriever
from rag_code.logger import get_logger, setup_logging

logger = get_logger(__name__)

INDEX_FILE_NAME = "faiss.index"
METADATA_FILE_NAME = "chunks_metadata.json"

EVAL_DIR = BASE_DIR / "data" / "eval"
EVAL_CASES_PATH = EVAL_DIR / "eval_cases.json"
RESULTS_CSV_PATH = EVAL_DIR / "ragas_results.csv"
SUMMARY_JSON_PATH = EVAL_DIR / "ragas_summary.json"


def load_eval_cases(file_path: Path) -> list[dict]:
    if not file_path.exists():
        raise FileNotFoundError(f"Evaluation file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("Evaluation file must contain a list of cases")

    return data


def extract_contexts(chunks: list[dict]) -> list[str]:
    return [chunk["text"] for chunk in chunks]

def normalize_text_for_csv(text: str) -> str:
    result = " ".join(text.split())
    return result

def unique_in_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    results: list[str] = []

    for item in items:
        if item not in seen:
            seen.add(item)
            results.append(item)

    return results

def build_answer_preview(answer: str, max_length: int = 160) -> str:
    cleaned = normalize_text_for_csv(answer)

    if len(cleaned) <= max_length:
        return cleaned
    
    return cleaned[: max_length - 3].rstrip() + "..."


def build_rag_pipeline() -> tuple[FaissRetriever, CrossEncoderReranker, OpenAIChatGenerator]:
    retriever = FaissRetriever(
        embedding_model_name=settings.embedding_model_name,
        index_path=INDEX_DIR / INDEX_FILE_NAME,
        metadata_path=INDEX_DIR / METADATA_FILE_NAME,
        top_k=settings.top_k,
    )

    reranker = CrossEncoderReranker(
        model_name=settings.reranker_model_name,
    )

    generator = OpenAIChatGenerator(
        model_name=settings.llm_model_name,
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
    )

    return retriever, reranker, generator

def build_ragas_metrics() -> tuple[Faithfulness, AnswerRelevancy, ContextPrecision, ContextRecall]:
    evaluator_client = AsyncOpenAI(
        api_key=settings.eval_llm_api_key,
        base_url=settings.eval_llm_base_url or None,
        http_client=DefaultAsyncHttpxClient(
            trust_env=False,
        ),
    )

    evaluator_llm = llm_factory(
        settings.eval_llm_model_name,
        client=evaluator_client,
        temperature=0,
    )

    evaluator_embeddings = HuggingFaceEmbeddings(
        model=settings.embedding_model_name,
    )

    faithfulness_metric = Faithfulness(llm=evaluator_llm)
    answer_relevancy_metric = AnswerRelevancy(
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
    )
    context_precision_metric = ContextPrecision(llm=evaluator_llm)
    context_recall_metric = ContextRecall(llm=evaluator_llm)

    return (
        faithfulness_metric,
        answer_relevancy_metric,
        context_precision_metric,
        context_recall_metric,
    )

def run_single_case(
    case: dict,
    retriever: FaissRetriever,
    reranker: CrossEncoderReranker,
    generator: OpenAIChatGenerator,
    faithfulness_metric: Faithfulness,
    answer_relevancy_metric: AnswerRelevancy,
    context_precision_metric: ContextPrecision,
    context_recall_metric: ContextRecall,
) -> dict:
    case_id = case["id"]
    query = case["query"]
    reference = case["reference"]

    faiss_results = retriever.retrieve(
        query=query,
        top_k=settings.top_k,
    )

    reranked_chunks = reranker.rerank(
        query=query,
        candidates=faiss_results,
        top_n=settings.rerank_top_n,
    )

    generation_result = generator.generate_answer(
        query=query,
        chunks=reranked_chunks,
    )

    answer = generation_result["answer"]
    retrieved_contexts = extract_contexts(reranked_chunks)

    faithfulness_result = faithfulness_metric.score(
        user_input=query,
        response=answer,
        retrieved_contexts=retrieved_contexts,
    )

    answer_relevancy_result = answer_relevancy_metric.score(
        user_input=query,
        response=answer,
    )

    context_precision_result = context_precision_metric.score(
        user_input=query,
        reference=reference,
        retrieved_contexts=retrieved_contexts,
    )

    context_recall_result = context_recall_metric.score(
        user_input=query,
        reference=reference,
        retrieved_contexts=retrieved_contexts,
    )

    retrieved_files = unique_in_order([chunk["file_name"] for chunk in reranked_chunks])
    retrieved_chunk_ids = [chunk["chunk_id"] for chunk in reranked_chunks]

    return {
    "id": case_id,
    "query": query,
    "reference": reference,
    "answer": answer,
    "answer_preview": build_answer_preview(answer),
    "retrieved_files": " | ".join(retrieved_files),
    "retrieved_chunk_ids": " | ".join(retrieved_chunk_ids),
    "retrieved_chunks_count": len(reranked_chunks),
    "faithfulness": float(faithfulness_result.value),
    "answer_relevancy": float(answer_relevancy_result.value),
    "context_precision": float(context_precision_result.value),
    "context_recall": float(context_recall_result.value),
}


def save_results_csv(rows: list[dict], file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id",
        "query",
        "reference",
        "answer_preview",
        "retrieved_files",
        "retrieved_chunk_ids",
        "retrieved_chunks_count",
        "faithfulness",
        "answer_relevancy",
        "context_precision",
        "context_recall",
        "answer_full",
    ]

    prepared_rows: list[dict] = []

    for row in rows:
        prepared_rows.append(
            {
                "id": row["id"],
                "query": normalize_text_for_csv(row["query"]),
                "reference": normalize_text_for_csv(row["reference"]),
                "answer_preview": row["answer_preview"],
                "retrieved_files": row["retrieved_files"],
                "retrieved_chunk_ids": row["retrieved_chunk_ids"],
                "retrieved_chunks_count": row["retrieved_chunks_count"],
                "faithfulness": f'{row["faithfulness"]:.4f}',
                "answer_relevancy": f'{row["answer_relevancy"]:.4f}',
                "context_precision": f'{row["context_precision"]:.4f}',
                "context_recall": f'{row["context_recall"]:.4f}',
                "answer_full": normalize_text_for_csv(row["answer"]),
            }
        )

    with file_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
        writer.writerows(prepared_rows)


def build_summary(rows: list[dict]) -> dict:
    return {
        "num_cases": len(rows),
        "avg_faithfulness": mean(row["faithfulness"] for row in rows),
        "avg_answer_relevancy": mean(row["answer_relevancy"] for row in rows),
        "avg_context_precision": mean(row["context_precision"] for row in rows),
        "avg_context_recall": mean(row["context_recall"] for row in rows),
    }


def save_summary_json(summary: dict, file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)


def main() -> None:
    setup_logging(settings.log_level)
    logger.info("Starting RAGAS evaluation")

    cases = load_eval_cases(EVAL_CASES_PATH)

    retriever, reranker, generator = build_rag_pipeline()

    (
        faithfulness_metric,
        answer_relevancy_metric,
        context_precision_metric,
        context_recall_metric,
    ) = build_ragas_metrics()

    rows: list[dict] = []

    for case in cases:
        row = run_single_case(
            case=case,
            retriever=retriever,
            reranker=reranker,
            generator=generator,
            faithfulness_metric=faithfulness_metric,
            answer_relevancy_metric=answer_relevancy_metric,
            context_precision_metric=context_precision_metric,
            context_recall_metric=context_recall_metric,
        )
        rows.append(row)

        logger.info("Finished case %s", row["id"])
        logger.info("Query: %s", row["query"])
        logger.info("Faithfulness: %.4f", row["faithfulness"])
        logger.info("Answer Relevancy: %.4f", row["answer_relevancy"])
        logger.info("Context Precision: %.4f", row["context_precision"])
        logger.info("Context Recall: %.4f", row["context_recall"])

    summary = build_summary(rows)

    save_results_csv(rows, RESULTS_CSV_PATH)
    save_summary_json(summary, SUMMARY_JSON_PATH)

    logger.info("RAGAS evaluation finished")
    logger.info("Cases: %d", summary["num_cases"])
    logger.info("Average Faithfulness: %.4f", summary["avg_faithfulness"])
    logger.info("Average Answer Relevancy: %.4f", summary["avg_answer_relevancy"])
    logger.info("Average Context Precision: %.4f", summary["avg_context_precision"])
    logger.info("Average Context Recall: %.4f", summary["avg_context_recall"])
    logger.info("Detailed results saved to: %s", RESULTS_CSV_PATH)
    logger.info("Summary saved to: %s", SUMMARY_JSON_PATH)


if __name__ == "__main__":
    main()