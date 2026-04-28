from sentence_transformers import CrossEncoder

class CrossEncoderReranker:
    def __init__(self, model_name: str, max_length: int | None = None) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self.model = CrossEncoder(
            model_name,
            max_length=max_length,
        )

    def rerank(self, query:str, candidates: list[dict], top_n: int | None = None,) -> list[dict]:
        query = query.strip()

        if not query:
            raise ValueError("query must not be empty")
        
        if not candidates:
            return[]
        
        sentence_pairs = [(query, item["text"]) for item in candidates]

        scores = self.model.predict(
            sentence_pairs,
            show_progress_bar=False,
        )

        reranked_results: list[dict] = []

        for item, score in zip(candidates, scores):
            reranked_item = item.copy()
            reranked_item["rerank_score"] = float(score)
            reranked_results.append(reranked_item)

        reranked_results.sort(
            key=lambda item: item["rerank_score"],
            reverse=True
        )

        if top_n is not None:
            reranked_results = reranked_results[:top_n]

        for rank, item in enumerate(reranked_results, start=1):
            item["rerank_rank"] = rank

        return reranked_results