from app.extractors.document_type_classifier import DocumentTypeClassifier
from app.schemas.common import DocumentType


def test_document_type_classifier_detects_cv() -> None:
    text = """
    Иван Иванов
    Опыт работы
    Python-разработчик

    Навыки
    Python, FastAPI, PostgreSQL

    Образование
    Южный федеральный университет
    """

    classifier = DocumentTypeClassifier()

    assert classifier.classify_text(text) == DocumentType.CV


def test_document_type_classifier_detects_cover_letter() -> None:
    text = """
    Уважаемый HR-специалист!

    Хочу откликнуться на вакансию Python-разработчика.
    Прошу рассмотреть мою кандидатуру.
    """

    classifier = DocumentTypeClassifier()

    assert classifier.classify_text(text) == DocumentType.COVER_LETTER


def test_document_type_classifier_detects_candidate_form() -> None:
    text = """
    Анкета кандидата

    ФИО: Иванов Иван Иванович
    Дата рождения: 01.01.2000
    Гражданство: РФ
    Желаемая должность: Python-разработчик
    """

    classifier = DocumentTypeClassifier()

    assert classifier.classify_text(text) == DocumentType.CANDIDATE_FORM


def test_document_type_classifier_detects_vacancy() -> None:
    text = """
    Вакансия: Python-разработчик

    Обязанности:
    Разработка backend-сервисов.

    Требования:
    Python, FastAPI, PostgreSQL.

    Условия:
    Удалённая работа.
    """

    classifier = DocumentTypeClassifier()

    assert classifier.classify_text(text) == DocumentType.VACANCY


def test_document_type_classifier_returns_unknown() -> None:
    text = "Просто небольшой текст без понятной структуры."

    classifier = DocumentTypeClassifier()

    assert classifier.classify_text(text) == DocumentType.UNKNOWN