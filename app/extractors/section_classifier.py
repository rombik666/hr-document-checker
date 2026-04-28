from app.schemas.documents import ParsedDocument


class SectionClassifier:
    """
    Классифицирует секции документа по смыслу.

    На этапе парсинга секции имеют типы:
    - paragraph;
    - table;
    - page.

    После классификации часть секций получит смысловые типы:
    - contacts;
    - experience;
    - skills;
    - education;
    - projects;
    - summary;
    - unknown.
    """

    SECTION_KEYWORDS: dict[str, list[str]] = {
        "contacts": [
            "контакты",
            "contact",
            "email",
            "e-mail",
            "телефон",
            "phone",
            "github",
            "telegram",
        ],
        "experience": [
            "опыт",
            "опыт работы",
            "work experience",
            "experience",
            "employment",
            "профессиональный опыт",
        ],
        "skills": [
            "навыки",
            "skills",
            "стек",
            "технологии",
            "technologies",
            "hard skills",
            "ключевые навыки",
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
        ],
        "projects": [
            "проекты",
            "projects",
            "портфолио",
            "portfolio",
            "pet-project",
            "pet project",
        ],
        "summary": [
            "о себе",
            "about me",
            "summary",
            "profile",
            "цель",
            "objective",
        ],
    }

    def classify(self, parsed_document: ParsedDocument) -> ParsedDocument:
        for section in parsed_document.sections:
            original_section_type = section.section_type
            predicted_type = self.classify_text(section.text)

            section.metadata["original_section_type"] = original_section_type
            section.section_type = predicted_type

        return parsed_document

    def classify_text(self, text: str) -> str:
        normalized_text = text.lower()

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