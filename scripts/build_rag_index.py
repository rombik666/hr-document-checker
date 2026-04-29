import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.core.logging import setup_logging
from app.rag.index_builder import RagIndexBuilder


def main() -> None:
    setup_logging()

    builder = RagIndexBuilder()
    result = builder.build()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()