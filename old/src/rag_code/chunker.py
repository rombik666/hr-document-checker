def split_text_into_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[dict]:
    if chunk_size <= 0:
        raise ValueError("chunk size must be greater than 0")
    
    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must be greater or equal to 0")
    
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")
    
    chunks: list[dict] = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        
        if end < text_length:
            last_newline = text.rfind("\n", start, end)
            last_space = text.rfind(" ", start, end)
            boundary = max(last_newline, last_space)

            if boundary > (start + chunk_size // 2):
                end = boundary
        
        raw_chunk = text[start:end]
        cleaned_chunk = raw_chunk.strip()

        if cleaned_chunk:
            left_trim = len(raw_chunk) - len(raw_chunk.lstrip())
            right_trim = len(raw_chunk) - len(raw_chunk.rstrip())

            chunks.append(
                {
                    "text": cleaned_chunk,
                    "start_char": start + left_trim,
                    "end_char": end - right_trim,
                }
            )

        if end == text_length:
            break

        next_start = max(end - chunk_overlap, 0)
        start = align_chunk_start(text, next_start)

    return chunks

def chunk_documents(documents: list[dict], chunk_size: int, chunk_overlap: int) -> list[dict]:
    all_chunks: list[dict] = []

    for document in documents:
        text_chunks = split_text_into_chunks(
            text = document["text"],
            chunk_size = chunk_size,
            chunk_overlap = chunk_overlap,
        )

        for local_chunk_id, chunk in enumerate(text_chunks):
            all_chunks.append(
                {
                    "chunk_id": f'{document["doc_id"]}_{local_chunk_id}',
                    "doc_id": document["doc_id"],
                    "source": document["source"],
                    "file_name": document["file_name"],
                    "text": chunk["text"],
                    "start_char": chunk["start_char"],
                    "end_char": chunk["end_char"],
                }
            )
    return all_chunks

def align_chunk_start(text:str, start: int) -> int:
    text_length = len(text)

    if (start <= 0) or (start >= text_length):
        return start
    
    if text[start].isspace():
        while (start < text_length) and (text[start].isspace()):
            start += 1
        return start
    
    if not text[start - 1].isspace():
        while (start < text_length) and not (text[start].isspace()):
            start += 1

    while (start < text_length) and (text[start].isspace()):
        start += 1

    return start