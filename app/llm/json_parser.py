import json
import re
from typing import Any


JSON_BLOCK_PATTERN = re.compile(
    r"```(?:json)?\s*(.*?)\s*```",
    re.DOTALL | re.IGNORECASE,
)


def extract_json_from_text(text: str) -> dict[str, Any]:

    stripped = text.strip()

    if not stripped:
        raise ValueError("Empty LLM response.")

    # Case 1: direct JSON.
    try:
        parsed = json.loads(stripped)

        if isinstance(parsed, dict):
            return parsed

        raise ValueError("LLM JSON response must be an object.")

    except json.JSONDecodeError:
        pass

    # Case 2: fenced code block.
    block_match = JSON_BLOCK_PATTERN.search(stripped)

    if block_match:
        block_content = block_match.group(1).strip()
        parsed = json.loads(block_content)

        if isinstance(parsed, dict):
            return parsed

        raise ValueError("LLM JSON block must be an object.")

    # Case 3: embedded JSON object.
    start = stripped.find("{")
    end = stripped.rfind("}")

    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        parsed = json.loads(candidate)

        if isinstance(parsed, dict):
            return parsed

    raise ValueError("Cannot extract JSON object from LLM response.")