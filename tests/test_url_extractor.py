from app.extractors.url_extractor import URLExtractor
from app.schemas.common import EntityType


def test_url_extractor_extracts_https_url() -> None:
    text = "Мой GitHub: https://github.com/ivan"

    extractor = URLExtractor()
    entities = extractor.extract(text)

    assert len(entities) == 1
    assert entities[0].entity_type == EntityType.URL
    assert entities[0].value == "https://github.com/ivan"


def test_url_extractor_normalizes_www_url() -> None:
    text = "Портфолио: www.example.com"

    extractor = URLExtractor()
    entities = extractor.extract(text)

    assert len(entities) == 1
    assert entities[0].normalized_value == "https://www.example.com"