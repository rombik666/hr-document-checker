# Cross-Encoder Reranking

A cross-encoder receives a **pair** of texts: a query and a candidate chunk.

Unlike a bi-encoder, it does not embed the query and document independently for fast retrieval. Instead, it processes the pair together and produces a more accurate relevance score.

In practice, cross-encoders are slower than vector search, so they are usually applied **after** the initial FAISS retrieval step. A common strategy is:

1. Retrieve top-k chunks with FAISS.
2. Score those chunks with a cross-encoder.
3. Keep the best reranked chunks for the final prompt.
