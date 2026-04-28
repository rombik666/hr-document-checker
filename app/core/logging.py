import logging
import sys


LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | "
    "%(message)s"
)


def setup_logging() -> None:
    """
    Настраивает базовое логирование приложения.

    Важно:
    - не логируем raw_text;
    - не логируем содержимое документов;
    - не логируем email, телефоны и текст вакансии.
    """

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )

    # Снижаем шум от некоторых библиотек.
    logging.getLogger("multipart").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Возвращает logger для конкретного модуля.
    """

    return logging.getLogger(name)