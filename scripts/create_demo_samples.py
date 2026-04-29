from pathlib import Path

from docx import Document


SAMPLES_DIR = Path("data/samples")


def save_docx(filename: str, paragraphs: list[str]) -> None:
    document = Document()

    for paragraph in paragraphs:
        document.add_paragraph(paragraph)

    file_path = SAMPLES_DIR / filename
    document.save(file_path)


def main() -> None:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    save_docx(
        "demo_cv_good.docx",
        [
            "Иван Иванов",
            "Контакты:",
            "Email: ivan@example.com",
            "Телефон: +7 999 123-45-67",
            "GitHub: https://github.com/ivan",
            "Навыки:",
            "Python, FastAPI, PostgreSQL, Docker, Git, REST API",
            "Опыт работы:",
            "Python backend developer, 2021-2024",
            "Разработал REST API на FastAPI для обработки заявок пользователей.",
            "Настроил хранение данных в PostgreSQL и Docker Compose для локального стенда.",
            "Образование:",
            "Южный федеральный университет, Программная инженерия",
        ],
    )

    save_docx(
        "demo_cv_missing_contacts.docx",
        [
            "Иван Иванов",
            "Навыки:",
            "Python, FastAPI, PostgreSQL",
            "Опыт работы:",
            "Python-разработчик, 2021-2024",
            "Образование:",
            "Южный федеральный университет",
        ],
    )

    save_docx(
        "demo_cv_weak_phrases.docx",
        [
            "Иван Иванов",
            "Контакты:",
            "Email: ivan@example.com",
            "Телефон: +7 999 123-45-67",
            "Навыки:",
            "Python, Git",
            "Опыт работы:",
            "Backend developer, 2023-2024",
            "Занимался разработкой backend.",
            "Работал с базой данных.",
            "Ответственный, коммуникабельный, быстро обучаюсь.",
            "Образование:",
            "Южный федеральный университет",
        ],
    )

    save_docx(
        "demo_cover_letter.docx",
        [
            "Уважаемый HR-специалист!",
            "Хочу откликнуться на вакансию Python-разработчика.",
            "Меня заинтересовала возможность работать с backend-сервисами.",
            "Имею опыт разработки Telegram-ботов, интеграции внешних API и работы с PostgreSQL.",
            "Прошу рассмотреть мою кандидатуру.",
        ],
    )

    save_docx(
        "demo_candidate_form.docx",
        [
            "Анкета кандидата",
            "ФИО: Иванов Иван Иванович",
            "Дата рождения: 01.01.2000",
            "Гражданство: РФ",
            "Желаемая должность: Python-разработчик",
            "Email: ivan@example.com",
            "Телефон: +7 999 123-45-67",
        ],
    )

    print(f"Demo samples created in: {SAMPLES_DIR.resolve()}")


if __name__ == "__main__":
    main()