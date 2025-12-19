# Pyannote Diarization Setup (Admin)

Goal: enable pyannote diarization under `backend/models/huggingface/pyannote` and run it in Selenite.

## Prereqs
- Run all commands from the repository root (the snippets use `backend/...` relative paths).
- ffmpeg installed and on PATH.
- Hugging Face token available (env `HF_TOKEN` or CLI login).

## 1) Install required Python packages
Recommended, stable stack for pyannote (CPU-only):
```
.\.venv\Scripts\pip install -r requirements-pyannote.txt --extra-index-url https://download.pytorch.org/whl/cpu
```
This pins torch/torchaudio to versions known to work with pyannote 3.1.x and keeps `weights_only` behavior compatible.

Verify imports:
```
.\.venv\Scripts\python - <<'PY'
try:
    import pyannote.audio  # type: ignore
    import torch
    print("pyannote.audio OK, torch", torch.__version__)
except Exception as e:
    print("FAILED", type(e).__name__, e)
PY
```
If this prints "OK", proceed. If torchaudio errors, reinstall torchaudio to match torch.

## 2) Download diarization weights
Place the main pipeline under the registry root:
```
@'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="pyannote/speaker-diarization-3.1",
    local_dir="backend/models/huggingface/pyannote/speaker-diarization-3.1",
    local_dir_use_symlinks=False,
)
'@ | .\backend\.venv\Scripts\python -
```
Keep existing subfolders (e.g., `segmentation-3.0`, `wespeaker-voxceleb-resnet34-LM`); do not delete anything under `/backend/models`.

## 3) Registry configuration
- In Admin → Model Registry, ensure the diarizer entry points to `backend/models/huggingface/pyannote` and is enabled.

## 4) Restart and test
- Restart: `.\scripts\restart-selenite.ps1`.
- Run a job with diarization enabled and select `pyannote`. The modal should show `pyannote` (no “failed”) and a detected speaker count >1 when present.

## 5) Troubleshooting
- Import fails: reinstall torchaudio to match torch; ensure `pyannote.audio` is in the backend venv.
- Model not found: verify registry path and that `speaker-diarization-3.1` exists under `backend/models/huggingface/pyannote/`.
- Runtime failure: check backend logs for "diarization failed". If you see `weights_only` errors, ensure you installed via `requirements-pyannote.txt` (above) and restart. Avoid deleting anything in `/backend/models`.
