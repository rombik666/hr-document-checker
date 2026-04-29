import json
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.services.backup_service import BackupService


BACKUP_DIR = Path("backups")


def main() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    init_db()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"backup_{timestamp}.json"

    db = SessionLocal()

    try:
        service = BackupService(db)
        payload = service.create_backup_payload()

        backup_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(f"Backup created: {backup_path}")
        print(f"Documents: {len(payload['documents'])}")
        print(f"Reports: {len(payload['reports'])}")

    finally:
        db.close()


if __name__ == "__main__":
    main()