"""Tests for capability reporting service."""

import importlib.util
from types import SimpleNamespace

import pytest
from httpx import AsyncClient, ASGITransport

from app.config import settings
from app.main import app
from app.models.user import User
from app.routes.system import get_current_user
from app.services.capabilities import (
    enforce_runtime_diarizer,
    get_asr_candidate_order,
    get_capabilities,
)
from app.services.system_probe import SystemProbeService


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, username="admin", email="admin@test"
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def mock_probe(monkeypatch):
    payload = {
        "gpu": {
            "has_gpu": True,
            "devices": [{"name": "Mock GPU", "memory_gb": 16.0, "multi_processor_count": 64}],
        }
    }
    monkeypatch.setattr(SystemProbeService, "get_cached_probe", lambda: payload)
    yield


def test_get_capabilities(monkeypatch):
    """Ensure capability response respects module availability."""
    monkeypatch.setattr(
        importlib.util, "find_spec", lambda name: None if name == "pyannote.audio" else True
    )
    result = get_capabilities()
    assert result["asr"][0]["available"] is True
    diarizers = {d["key"]: d for d in result["diarizers"]}
    assert diarizers["whisperx"]["available"] is True
    assert diarizers["pyannote"]["available"] is False


@pytest.mark.asyncio
async def test_capabilities_endpoint(monkeypatch):
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/system/availability")
    assert response.status_code == 200
    data = response.json()
    assert len(data["asr"]) >= 1
    assert len(data["diarizers"]) >= 1


def test_enforce_runtime_diarizer_prefers_job(monkeypatch):
    monkeypatch.setattr(
        "app.services.capabilities.get_capabilities",
        lambda: {
            "asr": [],
            "diarizers": [
                {"key": "whisperx", "available": True},
                {"key": "vad", "available": True},
            ],
        },
    )
    user_settings = SimpleNamespace(diarization_enabled=True, default_diarizer="vad")
    result = enforce_runtime_diarizer(
        requested_diarizer="whisperx",
        diarization_requested=True,
        user_settings=user_settings,
    )
    assert result["diarizer"] == "whisperx"
    assert result["diarization_enabled"] is True
    assert result["notes"] == []


def test_enforce_runtime_diarizer_fallback_to_admin(monkeypatch):
    monkeypatch.setattr(
        "app.services.capabilities.get_capabilities",
        lambda: {
            "asr": [],
            "diarizers": [
                {"key": "pyannote", "available": False, "notes": ["missing module"]},
                {"key": "whisperx", "available": True, "notes": []},
                {"key": "vad", "available": True, "notes": []},
            ],
        },
    )
    user_settings = SimpleNamespace(diarization_enabled=True, default_diarizer="whisperx")
    result = enforce_runtime_diarizer(
        requested_diarizer="pyannote",
        diarization_requested=True,
        user_settings=user_settings,
    )
    assert result["diarizer"] == "whisperx"
    assert result["diarization_enabled"] is True
    assert result["notes"]
    assert any("admin default" in note.lower() for note in result["notes"])


def test_enforce_runtime_diarizer_disables_when_none_available(monkeypatch):
    monkeypatch.setattr(
        "app.services.capabilities.get_capabilities",
        lambda: {
            "asr": [],
            "diarizers": [
                {"key": "whisperx", "available": False, "notes": ["no gpu"]},
                {"key": "pyannote", "available": False, "notes": ["no gpu"]},
                {"key": "vad", "available": False, "notes": ["not installed"]},
            ],
        },
    )
    user_settings = SimpleNamespace(diarization_enabled=True, default_diarizer="whisperx")
    result = enforce_runtime_diarizer(
        requested_diarizer="whisperx",
        diarization_requested=True,
        user_settings=user_settings,
    )
    assert result["diarizer"] is None
    assert result["diarization_enabled"] is False
    assert "disabling speaker labels" in result["notes"][-1].lower()


def test_get_asr_candidate_order_deduplicates(monkeypatch):
    monkeypatch.setattr(settings, "default_whisper_model", "small")
    user_settings = SimpleNamespace(default_model="large-v3")
    order = get_asr_candidate_order("tiny", user_settings)
    assert order == ["tiny", "large-v3", "small", "medium"]
