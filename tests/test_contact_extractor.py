from app.extractors.contact_extractor import ContactExtractor
from app.schemas.common import EntityType


def test_contact_extractor_extracts_email() -> None:
    text = "Связаться со мной можно по email: ivan@example.com"

    extractor = ContactExtractor()
    entities = extractor.extract(text)

    assert len(entities) == 1
    assert entities[0].entity_type == EntityType.EMAIL
    assert entities[0].value == "ivan@example.com"
    assert entities[0].normalized_value == "ivan@example.com"


def test_contact_extractor_extracts_phone() -> None:
    text = "Телефон: +7 999 123-45-67"

    extractor = ContactExtractor()
    entities = extractor.extract(text)

    phones = [entity for entity in entities if entity.entity_type == EntityType.PHONE]

    assert len(phones) == 1
    assert phones[0].value == "+7 999 123-45-67"
    assert phones[0].normalized_value == "+79991234567"


def test_contact_extractor_extracts_email_and_phone() -> None:
    text = "Email: ivan@example.com, телефон: 8 (999) 123-45-67"

    extractor = ContactExtractor()
    entities = extractor.extract(text)

    entity_types = {entity.entity_type for entity in entities}

    assert EntityType.EMAIL in entity_types
    assert EntityType.PHONE in entity_types