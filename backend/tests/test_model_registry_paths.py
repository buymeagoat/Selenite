from pathlib import Path

import pytest

from app.services.model_registry import ModelRegistryService


@pytest.fixture
def patched_models_root(tmp_path):
    original_models_root = ModelRegistryService._MODELS_ROOT
    original_legacy_root = ModelRegistryService._LEGACY_MODELS_ROOT
    ModelRegistryService._MODELS_ROOT = (tmp_path / "models").resolve()
    ModelRegistryService._LEGACY_MODELS_ROOT = (tmp_path / "legacy").resolve()
    yield
    ModelRegistryService._MODELS_ROOT = original_models_root
    ModelRegistryService._LEGACY_MODELS_ROOT = original_legacy_root


def test_rebases_paths_from_other_clone(patched_models_root):
    foreign_path = Path(r"C:\example\OtherClone\backend\models\whisper\base")
    rebased = ModelRegistryService._resolve_path(str(foreign_path))
    expected = (ModelRegistryService._MODELS_ROOT / "whisper" / "base").resolve()
    assert rebased == expected


def test_rejects_non_model_paths(patched_models_root, tmp_path):
    elsewhere = (tmp_path / "elsewhere").resolve()
    with pytest.raises(ValueError):
        ModelRegistryService._validate_set_path(str(elsewhere))
