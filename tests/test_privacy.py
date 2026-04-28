from app.core.privacy import contains_personal_data, mask_email, mask_phone, mask_text


def test_mask_email() -> None:
    assert mask_email("ivan@example.com") == "i***@example.com"


def test_mask_phone_with_plus_seven() -> None:
    assert mask_phone("+7 999 123-45-67") == "+7 *** ***-**-67"


def test_mask_phone_with_eight() -> None:
    assert mask_phone("8 (999) 123-45-67") == "+7 *** ***-**-67"


def test_mask_text_masks_email_and_phone() -> None:
    text = "Email: ivan@example.com, телефон: +7 999 123-45-67"

    masked = mask_text(text)

    assert "ivan@example.com" not in masked
    assert "+7 999 123-45-67" not in masked
    assert "i***@example.com" in masked
    assert "+7 *** ***-**-67" in masked


def test_contains_personal_data() -> None:
    assert contains_personal_data("Email: ivan@example.com")
    assert contains_personal_data("Телефон: +7 999 123-45-67")
    assert not contains_personal_data("Просто текст без контактов")