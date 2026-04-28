from openai import OpenAI, DefaultHttpxClient

from rag_code.logger import get_logger

logger = get_logger(__name__)

class OpenAIChatGenerator:
    def __init__(self, model_name: str, api_key: str | None, base_url:str | None = None,) -> None:
        if not api_key:
            logger.error("LLM_API_KEY is not set before generator initialization")
            raise ValueError(
                "LLM_API_KEY is not set. Add it to your .env file before generation."
            )

        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url

        logger.info(
            "Initializing generator | model=%s | base_url=%s",
            model_name,
            base_url,
        )

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=DefaultHttpxClient(
                trust_env=False,
            ),
        )

    @staticmethod
    def build_context(chunks: list[dict]) -> str:
        context_blocks: list[dict] = []

        for item in chunks:
            block = "\n".join(
                [
                    f'Source: {item["source"]}',
                    f'File: {item["file_name"]}',
                    f'Chunk ID: {item["chunk_id"]}',
                    "Text:",
                    item["text"],
                ]
            )
            context_blocks.append(block)
        
        return "\n\n".join(context_blocks)
    
    @staticmethod
    def build_messages(query: str, context:str) -> list[dict]:
        developer_message = (
            "You are a helpful assistant in a Retrieval-Augmented Generation system.\n"
            "Answer the user's question using only the provided context.\n"
            "If the context is insufficient, explicitly say that the answer was not found "
            "in the retrieved documents.\n"
            "Do not invent facts.\n"
            "When possible, mention the source file names that support the answer."
        )

        user_message = (
            f"User question:\n{query}\n\n"
            f"Retrieved context:\n{context}"
        )

        return [
            {"role": "system", "content": developer_message},
            {"role": "user", "content": user_message},
        ]
    
    def generate_answer(self, query:str, chunks: list[dict]) -> dict:
        query = query.strip()

        if not query:
            logger.error("Generator received empty query")
            raise ValueError("query must not be empty")
        
        if not chunks:
            logger.error("Generator received empty chunks for query=%r", query)
            raise ValueError("chunks must not be empty")
        
        logger.info(
            "Generating answer | query=%r | chunks=%d | model=%s",
            query,
            len(chunks),
            self.model_name,
        )
        
        context = self.build_context(chunks)
        messages = self.build_messages(query, context)

        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )

        answer = completion.choices[0].message.content or ""

        logger.info(
            "Generation finished | query=%r | answer_length=%d",
            query,
            len(answer.strip()),
        )

        return {
            "query": query,
            "answer": answer.strip(),
            "context": context,
            "used_chunks": chunks,
        }