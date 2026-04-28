# RAG Pipeline Overview

A simple RAG pipeline can be split into several stages:

## 1. Document processing
Documents are loaded from disk and normalized.

## 2. Chunking
Long texts are split into smaller overlapping chunks so that semantic meaning is preserved across boundaries.

## 3. Embeddings and indexing
Each chunk is converted into a dense vector using an embedding model. Those vectors are stored in a vector index such as FAISS.

## 4. Retrieval and reranking
The query is embedded, relevant chunks are retrieved from FAISS, and a cross-encoder reranks them.

## 5. Generation
The language model receives the user query plus the best chunks and produces the final answer.

## 6. Evaluation
RAG quality can be assessed with tools like RAGAS using metrics related to retrieval quality and answer faithfulness.
