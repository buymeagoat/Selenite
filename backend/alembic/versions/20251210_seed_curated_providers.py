"""Seed curated ASR/diarizer providers and create model directories.

- Creates provider/entry folders under backend/models (no weights).
- Inserts model_sets/model_entries records for curated providers if missing.
"""

from __future__ import annotations

from pathlib import Path

from alembic import op
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.model_provider import ModelEntry, ModelSet

# revision identifiers, used by Alembic.
revision = "20251210_seed_curated_providers"
down_revision = "20251209_add_transcode_to_wav"
branch_labels = None
depends_on = None


# Curated provider catalog (seeded disabled; admins drop weights then enable)
CURATED = {
    "asr": {
        "whisper": ["tiny", "base", "small", "medium", "large-v3"],
        "faster-whisper": ["tiny", "base", "medium-int8"],
        "wav2vec2": ["base-960h", "large-lv60"],
        "nemo": ["conformer-ctc-en"],
        "vosk": ["small-en-us", "large-en-us"],
        "coqui-stt": ["en-us"],
        "transformers": ["xls-r-300m", "wavlm-base"],
    },
    "diarizer": {
        "pyannote": ["diarization-3.1", "segmentation-3.0", "wespeaker-voxceleb-resnet34-LM"],
        "nemo-diarizer": ["offline"],
        "speechbrain": ["ecapa-diarization"],
        "resemblyzer": ["encoder-clustering"],
    },
}


def _backend_models_root() -> Path:
    # versions/<file>.py -> alembic -> backend
    return Path(__file__).resolve().parents[2] / "models"


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    models_root = _backend_models_root()
    models_root.mkdir(parents=True, exist_ok=True)

    try:
        for ptype, providers in CURATED.items():
            for provider, entries in providers.items():
                set_path = (models_root / provider).resolve()
                set_path.mkdir(parents=True, exist_ok=True)

                model_set = session.execute(
                    select(ModelSet).where(ModelSet.name == provider, ModelSet.type == ptype)
                ).scalars().first()
                if not model_set:
                    model_set = ModelSet(
                        type=ptype,
                        name=provider,
                        description=f"Seeded {ptype} provider '{provider}' (weights not included).",
                        abs_path=str(set_path),
                        enabled=False,
                        disable_reason="Seeded provider; add weights to enable.",
                    )
                    session.add(model_set)
                    session.flush()

                for entry in entries:
                    entry_path = (set_path / entry).resolve()
                    entry_path.mkdir(parents=True, exist_ok=True)

                    existing_entry = session.execute(
                        select(ModelEntry).where(
                            ModelEntry.set_id == model_set.id, ModelEntry.name == entry
                        )
                    ).scalars().first()
                    if existing_entry:
                        continue

                    session.add(
                        ModelEntry(
                            set_id=model_set.id,
                            type=ptype,
                            name=entry,
                            description=f"Seeded {ptype} entry '{entry}' (weights not included).",
                            abs_path=str(entry_path),
                            enabled=False,
                            disable_reason="Weights not present; drop files then enable.",
                        )
                    )
        session.commit()
    finally:
        session.close()


def downgrade() -> None:
    # No-op to avoid deleting admin data.
    pass
