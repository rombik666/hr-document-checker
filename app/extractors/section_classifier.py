from app.schemas.documents import ParsedDocument


class SectionClassifier:
    """
    Классифицирует секции документа по смыслу.

    """

    SECTION_KEYWORDS: dict[str, list[str]] = {
        "contacts": [
            "контакты",
            "contact",
            "contacts",
            "email",
            "e-mail",
            "телефон",
            "phone",
            "github",
            "telegram",
            "linkedin",
        ],
        "experience": [
            "опыт",
            "опыт работы",
            "work experience",
            "experience",
            "employment",
            "профессиональный опыт",
            "карьера",
        ],
        "skills": [
            "навыки",
            "skills",
            "стек",
            "технологии",
            "technologies",
            "hard skills",
            "ключевые навыки",
            "инструменты",
        ],
        "education": [
            "образование",
            "education",
            "университет",
            "university",
            "бакалавр",
            "магистр",
            "bachelor",
            "master",
            "юфу",
            "институт",
        ],
        "projects": [
            "проекты",
            "projects",
            "портфолио",
            "portfolio",
            "pet-project",
            "pet project",
            "github",
        ],
        "summary": [
            "о себе",
            "about me",
            "summary",
            "profile",
            "цель",
            "objective",
            "профиль",
        ],
    }

    STRONG_HEADINGS: dict[str, list[str]] = {
        "contacts": [
            "контакты",
            "contacts",
            "contact",
        ],
        "experience": [
            "опыт",
            "опыт работы",
            "work experience",
            "experience",
            "профессиональный опыт",
        ],
        "skills": [
            "навыки",
            "skills",
            "ключевые навыки",
            "technologies",
            "технологии",
            "стек",
        ],
        "education": [
            "образование",
            "education",
        ],
        "projects": [
            "проекты",
            "projects",
            "portfolio",
            "портфолио",
        ],
        "summary": [
            "о себе",
            "summary",
            "profile",
            "about me",
        ],
    }

    SECTION_ORDER = [
        "contacts",
        "summary",
        "experience",
        "skills",
        "education",
        "projects",
    ]

    def classify(self, parsed_document: ParsedDocument) -> ParsedDocument:
        current_context: str | None = None

        for section in parsed_document.sections:
            original_section_type = section.section_type
            predicted_type = self.classify_text(section.text)

            is_heading = self._is_heading(section.text)

            if predicted_type != "unknown":
                section.section_type = predicted_type

                if is_heading:
                    current_context = predicted_type

            elif current_context:
                section.section_type = current_context
                section.metadata["inherited_section_type"] = True

            else:
                section.section_type = "unknown"

            section.metadata["original_section_type"] = original_section_type

        return parsed_document

    def classify_text(self, text: str) -> str:
        normalized_text = self._normalize_text(text)

        if not normalized_text:
            return "unknown"

        # Сначала проверяем сильные заголовки.
        for section_type in self.SECTION_ORDER:
            headings = self.STRONG_HEADINGS.get(section_type, [])

            for heading in headings:
                if self._matches_heading(normalized_text, heading):
                    return section_type

        # Потом обычный keyword scoring.
        scores: dict[str, int] = {}

        for section_type, keywords in self.SECTION_KEYWORDS.items():
            score = 0

            for keyword in keywords:
                if keyword.lower() in normalized_text:
                    score += 1

            if score > 0:
                scores[section_type] = score

        if not scores:
            return "unknown"

        return max(scores, key=scores.get)

    @staticmethod
    def _normalize_text(text: str) -> str:
        return text.strip().lower().replace("ё", "е")

    @staticmethod
    def _is_heading(text: str) -> bool:
        stripped = text.strip()

        if not stripped:
            return False

        # Короткие строки с двоеточием обычно являются заголовками.
        if stripped.endswith(":") and len(stripped) <= 40:
            return True

        # Короткие строки капсом тоже часто являются заголовками.
        letters = [char for char in stripped if char.isalpha()]

        if letters:
            uppercase_letters = [char for char in letters if char.isupper()]

            if len(stripped) <= 40 and len(uppercase_letters) / len(letters) > 0.7:
                return True

        # Обычный заголовок без двоеточия.
        if len(stripped.split()) <= 4 and len(stripped) <= 35:
            return True

        return False

    @staticmethod
    def _matches_heading(normalized_text: str, heading: str) -> bool:
        heading = heading.lower().replace("ё", "е")

        variants = {
            heading,
            f"{heading}:",
            f"{heading}.",
            f"{heading} ",
        }

        return normalized_text in variants