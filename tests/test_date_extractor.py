from app.extractors.date_extractor import DateExtractor
from app.schemas.common import EntityType


def test_date_extractor_extracts_year_range() -> None:
    text = "Опыт работы: Python-разработчик, 2020-2023"

    extractor = DateExtractor()
    entities = extractor.extract(text)

    assert any(entity.value == "2020-2023" for entity in entities)
    assert all(entity.entity_type == EntityType.DATE for entity in entities)


def test_date_extractor_extracts_full_date() -> None:
    text = "Дата рождения: 01.02.2000"

    extractor = DateExtractor()
    entities = extractor.extract(text)

    assert any(entity.value == "01.02.2000" for entity in entities)


def test_date_extractor_extracts_month_year() -> None:
    text = "Работал с мая 2021 по декабрь 2023"

    extractor = DateExtractor()
    entities = extractor.extract(text)

    values = [entity.value.lower() for entity in entities]

    assert "мая 2021" in values
    assert "декабрь 2023" in values