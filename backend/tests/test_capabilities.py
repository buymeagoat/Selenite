"""Tests for capability reporting service."""

from types import SimpleNamespace

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.routes.system import get_current_user
from app.services.capabilities import (
    enforce_runtime_diarizer,
    get_asr_candidate_order,
    get_capabilities,
)
from app.services.provider_manager import ProviderManager, ProviderRecord


@pytest.fixture(autouse=True)
def override_auth():
    app.dependency_overrides[get_current_user] = lambda: User(
        id=1, username="admin", email="admin@test"
    )
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_get_capabilities_returns_empty_when_registry_missing(monkeypatch):
    monkeypatch.setattr(ProviderManager, "get_snapshot", lambda: {"asr": [], "diarizers": []})
    result = get_capabilities()
    assert result["asr"] == []
    assert result["diarizers"] == []


@pytest.mark.asyncio
async def test_capabilities_endpoint(monkeypatch):
    monkeypatch.setattr(ProviderManager, "get_snapshot", lambda: {"asr": [], "diarizers": []})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/system/availability")
    assert response.status_code == 200
    data = response.json()
    assert data["asr"] == []
    assert data["diarizers"] == []


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
    user_settings = SimpleNamespace(default_diarizer="vad")
    result = enforce_runtime_diarizer(
        requested_diarizer="whisperx",
        diarization_requested=True,
        user_settings=user_settings,
    )
    assert result["diarizer"] == "whisperx"
    assert result["diarization_enabled"] is True
    assert result["notes"] == []


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
    user_settings = SimpleNamespace(default_diarizer="whisperx")
    result = enforce_runtime_diarizer(
        requested_diarizer="whisperx",
        diarization_requested=True,
        user_settings=user_settings,
    )
    assert result["diarizer"] is None
    assert result["diarization_enabled"] is False
    assert "disabling speaker labels" in result["notes"][-1].lower()


def test_get_asr_candidate_order_deduplicates(monkeypatch):
    monkeypatch.setattr("app.services.capabilities._assess_record", lambda r: {"available": True})
    record = ProviderRecord(
        set_id=1,
        weight_id=1,
        set_name="faster-whisper",
        name="medium",
        provider_type="asr",
        abs_path="/backend/models/faster-whisper/medium",
        enabled=True,
        disable_reason=None,
        checksum=None,
    )
    monkeypatch.setattr(
        ProviderManager,
        "get_snapshot",
        lambda: {"asr": [record], "diarizers": []},
    )
    user_settings = SimpleNamespace(default_model="medium")
    order = get_asr_candidate_order("medium", user_settings)
    assert order == ["medium"]
