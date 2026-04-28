from abc import ABC, abstractmethod
from pathlib import Path

from app.schemas.documents import ParsedDocument


class DocumentParser(ABC):
    """
    Базовый интерфейс для всех парсеров документов.

    Нужен для того, чтобы DOCXParser и PDFParser имели одинаковый метод parse().
    Тогда агент-координатору в будущем будет неважно, какой именно формат файла
    был загружен пользователем.
    """

    @abstractmethod
    def parse(self, file_path: Path) -> ParsedDocument:
        raise NotImplementedError