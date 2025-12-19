"""Utilities for detecting configuration drift (paths, storage, etc.)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_provider import ModelEntry, ModelSet


@dataclass(frozen=True)
class AlignmentIssue:
    """Represents a drift finding."""

    category: str
    detail: str
    suggestion: str | None = None

    def format(self) -> str:
        if self.suggestion:
            return f"[{self.category}] {self.detail} (suggestion: {self.suggestion})"
        return f"[{self.category}] {self.detail}"


class AlignmentChecker:
    """
    Performs validation of filesystem locations and registry records to detect drift
    from canonical contracts (e.g., backend/models, storage/media, etc.).
    """

    def __init__(
        self,
        *,
        model_root: Path,
        storage_root: Path,
        backend_root: Path,
        project_root: Path,
        media_path: Path,
        transcript_path: Path,
        allow_test_storage: bool = False,
    ) -> None:
        self.model_root = model_root.resolve()
        self.storage_root = storage_root.resolve()
        self.backend_root = backend_root.resolve()
        self.project_root = project_root.resolve()
        self.media_path = media_path.resolve()
        self.transcript_path = transcript_path.resolve()
        self.allow_test_storage = allow_test_storage
        self.legacy_model_root = (self.project_root / "models").resolve()
        self.legacy_vitest_logs = (self.project_root / "vitest-logs").resolve()
        self.backend_storage_root = (self.backend_root / "storage").resolve()
        self.backend_scratch = (self.backend_root / "scratch").resolve()
        self.canonical_scratch = (self.project_root / "scratch").resolve()
        self.test_storage_root = (self.project_root / "scratch" / "tests").resolve()

    async def check_registry_paths(self, session: AsyncSession) -> List[AlignmentIssue]:
        issues: List[AlignmentIssue] = []

        sets: Sequence[ModelSet] = (
            (await session.execute(select(ModelSet).order_by(ModelSet.id))).scalars().all()
        )
        entries: Sequence[ModelEntry] = (
            (await session.execute(select(ModelEntry).order_by(ModelEntry.id))).scalars().all()
        )

        for model_set in sets:
            path = Path(model_set.abs_path).resolve()
            if not self._is_under_model_root(path):
                issues.append(
                    AlignmentIssue(
                        category="model_set",
                        detail=f"Model set '{model_set.name}' uses '{path}' outside backend/models.",
                        suggestion="Run scripts/check_alignment.py --fix or move the folder under backend/models.",
                    )
                )

        for entry in entries:
            path = Path(entry.abs_path).resolve()
            if not self._is_under_model_root(path):
                issues.append(
                    AlignmentIssue(
                        category="model_weight",
                        detail=f"Weight '{entry.name}' (set {entry.set_id}) uses '{path}' outside backend/models.",
                        suggestion="Update the weight path to backend/models/<set>/<weight>/…",
                    )
                )

        return issues

    def check_settings(self, *, media_path: Path, transcript_path: Path) -> List[AlignmentIssue]:
        issues: List[AlignmentIssue] = []
        media_resolved = media_path.resolve()
        transcript_resolved = transcript_path.resolve()
        media_ok = media_resolved.is_relative_to(self.storage_root)
        transcript_ok = transcript_resolved.is_relative_to(self.storage_root)
        if self.allow_test_storage:
            media_ok = media_ok or media_resolved.is_relative_to(self.test_storage_root)
            transcript_ok = transcript_ok or transcript_resolved.is_relative_to(
                self.test_storage_root
            )
        if not media_ok:
            issues.append(
                AlignmentIssue(
                    category="media_storage",
                    detail=f"MEDIA_STORAGE_PATH points to '{media_path}', expected under '{self.storage_root}'.",
                    suggestion="Set MEDIA_STORAGE_PATH to storage/media (or a child directory).",
                )
            )
        if not transcript_ok:
            issues.append(
                AlignmentIssue(
                    category="transcript_storage",
                    detail=f"TRANSCRIPT_STORAGE_PATH points to '{transcript_path}', expected under '{self.storage_root}'.",
                    suggestion="Set TRANSCRIPT_STORAGE_PATH to storage/transcripts (or a child directory).",
                )
            )
        return issues

    def check_filesystem(self) -> List[AlignmentIssue]:
        issues: List[AlignmentIssue] = []

        if self.legacy_model_root != self.model_root and self.legacy_model_root.exists():
            if any(self.legacy_model_root.iterdir()):
                issues.append(
                    AlignmentIssue(
                        category="legacy_models",
                        detail=f"Legacy models directory '{self.legacy_model_root}' still contains data.",
                        suggestion="Run scripts/check_alignment.py --fix or move contents into backend/models.",
                    )
                )
            else:
                issues.append(
                    AlignmentIssue(
                        category="legacy_models",
                        detail=f"Legacy models directory '{self.legacy_model_root}' should be removed (even though it is empty).",
                        suggestion="Delete the empty 'models' folder so only backend/models remains canonical.",
                    )
                )

        if self.backend_storage_root.exists() and any(self.backend_storage_root.iterdir()):
            issues.append(
                AlignmentIssue(
                    category="backend_storage",
                    detail=f"Found files under '{self.backend_storage_root}'. Canonical storage lives at '{self.storage_root}'.",
                    suggestion="Move media/transcripts to the storage/ root and remove backend/storage.",
                )
            )

        nested_backend = self.backend_root / "backend"
        if nested_backend.exists():
            issues.append(
                AlignmentIssue(
                    category="nested_backend",
                    detail=f"Found unexpected '{nested_backend}' directory (usually created by running `backend/...` commands from inside backend/).",
                    suggestion="Remove the nested folder (after copying any files to backend/models) and run future commands from the repo root.",
                )
            )

        if self.legacy_vitest_logs.exists():
            issues.append(
                AlignmentIssue(
                    category="legacy_logs",
                    detail=f"Found '{self.legacy_vitest_logs}' at the repo root; logs now belong under 'logs/'.",
                    suggestion="Move any Vitest output into logs/frontend and delete the legacy vitest-logs directory.",
                )
            )

        if self.backend_scratch.exists():
            issues.append(
                AlignmentIssue(
                    category="scratch",
                    detail=f"Found '{self.backend_scratch}' but only the repo-root 'scratch/' directory is supported.",
                    suggestion="Move notes/assets to the top-level scratch/ folder and remove backend/scratch.",
                )
            )

        for required in ("media", "transcripts"):
            path = self.storage_root / required
            if not path.exists():
                issues.append(
                    AlignmentIssue(
                        category="storage",
                        detail=f"Expected directory '{path}' does not exist.",
                        suggestion="Create the directory or update STORAGE paths accordingly.",
                    )
                )

        return issues

    def _is_under_model_root(self, path: Path) -> bool:
        resolved = path.resolve()
        try:
            resolved.relative_to(self.model_root)
            return True
        except ValueError:
            return False


async def gather_alignment_issues(
    *,
    session: AsyncSession,
    checker: AlignmentChecker,
) -> List[AlignmentIssue]:
    issues: List[AlignmentIssue] = []
    issues.extend(await checker.check_registry_paths(session))
    issues.extend(
        checker.check_settings(
            media_path=checker.media_path, transcript_path=checker.transcript_path
        )
    )
    issues.extend(checker.check_filesystem())
    return issues


def format_issues(issues: Iterable[AlignmentIssue]) -> str:
    return "\n".join(issue.format() for issue in issues)
