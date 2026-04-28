from app.schemas.common import DocumentType
from app.schemas.documents import ParsedDocument


class DocumentTypeClassifier:
    """
    Классификатор типа документа.

    """

    CV_KEYWORDS = [
        "резюме",
        "cv",
        "curriculum vitae",
        "опыт работы",
        "навыки",
        "образование",
        "проекты",
        "python-разработчик",
        "backend",
        "frontend",
        "developer",
    ]

    COVER_LETTER_KEYWORDS = [
        "сопроводительное письмо",
        "cover letter",
        "уважаемый",
        "уважаемая",
        "отклик",
        "хочу откликнуться",
        "рассмотреть мою кандидатуру",
        "заинтересовала вакансия",
    ]

    CANDIDATE_FORM_KEYWORDS = [
        "анкета кандидата",
        "candidate form",
        "фио",
        "дата рождения",
        "гражданство",
        "семейное положение",
        "желаемая должность",
    ]

    VACANCY_KEYWORDS = [
        "вакансия",
        "обязанности",
        "требования",
        "условия",
        "мы предлагаем",
        "работодатель",
        "зарплата",
        "график работы",
    ]

    def classify(self, document: ParsedDocument) -> ParsedDocument:
        document.metadata.document_type = self.classify_text(document.raw_text)
        return document

    def classify_text(self, text: str) -> DocumentType:
        normalized_text = text.lower()

        scores = {
            DocumentType.CV: self._score(normalized_text, self.CV_KEYWORDS),
            DocumentType.COVER_LETTER: self._score(normalized_text, self.COVER_LETTER_KEYWORDS),
            DocumentType.CANDIDATE_FORM: self._score(normalized_text, self.CANDIDATE_FORM_KEYWORDS),
            DocumentType.VACANCY: self._score(normalized_text, self.VACANCY_KEYWORDS),
        }

        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score == 0:
            return DocumentType.UNKNOWN

        return best_type

    @staticmethod
    def _score(text: str, keywords: list[str]) -> int:
        return sum(1 for keyword in keywords if keyword.lower() in text)