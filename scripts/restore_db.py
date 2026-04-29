import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.backup_service import BackupService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restore HR Document Checker database from JSON backup.",
    )

    parser.add_argument(
        "backup_path",
        type=str,
        help="Path to JSON backup file.",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    backup_path = Path(args.backup_path)

    if not backup_path.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_path}")

    init_db()

    payload = json.loads(
        backup_path.read_text(encoding="utf-8"),
    )

    db = SessionLocal()

    try:
        service = BackupService(db)
        result = service.restore_from_payload(payload)

        print("Restore completed.")
        print(f"Restored documents: {result['restored_documents']}")
        print(f"Restored reports: {result['restored_reports']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()