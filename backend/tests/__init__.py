"""Test configuration."""

from pathlib import Path
import os

os.environ["ENVIRONMENT"] = "testing"

# Guardrail: never run tests against the production DB.
db_url = os.environ.get("DATABASE_URL", "")
if not db_url or "backend/selenite.db" in db_url.replace("\\", "/"):
    repo_root = Path(__file__).resolve().parents[2]
    test_root = repo_root / "scratch" / "tests"
    test_db = test_root / "selenite.test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{test_db.as_posix()}"
    os.environ.setdefault("MEDIA_STORAGE_PATH", str(test_root / "media"))
    os.environ.setdefault("TRANSCRIPT_STORAGE_PATH", str(test_root / "transcripts"))
