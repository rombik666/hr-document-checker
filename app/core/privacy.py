import re


EMAIL_PATTERN = re.compile(
    r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?:(?:\+7|8)[\s\-()]*)"
    r"(?:\(?\d{3}\)?[\s\-()]*)"
    r"\d{3}[\s\-]*\d{2}[\s\-]*\d{2}"
)


def mask_email(email: str) -> str:

    if "@" not in email:
        return email

    local_part, domain = email.split("@", maxsplit=1)

    if not local_part:
        return "***@" + domain

    return local_part[0] + "***@" + domain


def mask_phone(phone: str) -> str:

    digits = re.sub(r"\D", "", phone)

    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]

    if len(digits) == 11 and digits.startswith("7"):
        return "+7 *** ***-**-" + digits[-2:]

    if len(digits) == 10:
        return "+7 *** ***-**-" + digits[-2:]

    return "***"


def mask_text(text: str) -> str:

    masked_text = EMAIL_PATTERN.sub(
        lambda match: mask_email(match.group(0)),
        text,
    )

    masked_text = PHONE_PATTERN.sub(
        lambda match: mask_phone(match.group(0)),
        masked_text,
    )

    return masked_text


def contains_personal_data(text: str) -> bool:

    return bool(EMAIL_PATTERN.search(text) or PHONE_PATTERN.search(text))