from fastapi import HTTPException, UploadFile


MAX_DOCUMENT_SIZE_BYTES = 3 * 1024 * 1024


async def read_document_upload(file: UploadFile) -> bytes:
    content = await file.read(MAX_DOCUMENT_SIZE_BYTES + 1)

    if len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Размер документа не должен превышать 3 МБ.",
        )

    return content
