"""Tests for the system probe service and routes."""

import pytest
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.models.user import User
from app.routes.system import get_current_user
from app.services.system_probe import SystemProbeService


@pytest.fixture(autouse=True)
def reset_probe_cache():
    """Ensure probe cache is cleared between tests."""
    SystemProbeService._cache = None  # type: ignore[attr-defined]
    yield
    SystemProbeService._cache = None  # type: ignore[attr-defined]


def _mock_payload():
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return {
        "detected_at": now,
        "os": {"system": "TestOS", "release": "1.0", "version": "1.0.0", "machine": "x86_64"},
        "cpu": {
            "model": "Example CPU",
            "architecture": "x86_64",
            "cores_physical": 4,
            "cores_logical": 8,
            "max_frequency_mhz": 3500,
        },
        "memory": {"total_gb": 16.0, "available_gb": 8.0},
        "gpu": {
            "has_gpu": True,
            "api": "cuda",
            "driver": "12.1",
            "devices": [{"name": "Mock GPU", "memory_gb": 12.0, "multi_processor_count": 64}],
        },
        "storage": {
            "database": {"path": "/tmp/db", "total_gb": 100.0, "used_gb": 10.0, "free_gb": 90.0},
            "media": {"path": "/tmp/media", "total_gb": 200.0, "used_gb": 20.0, "free_gb": 180.0},
            "transcripts": {
                "path": "/tmp/trans",
                "total_gb": 200.0,
                "used_gb": 30.0,
                "free_gb": 170.0,
            },
            "project": {
                "path": "/tmp/project",
                "total_gb": 300.0,
                "used_gb": 50.0,
                "free_gb": 250.0,
            },
        },
        "network": {
            "hostname": "selenite-host",
            "interfaces": [{"name": "eth0", "ipv4": ["192.168.1.10"]}],
        },
        "runtime": {"python": "3.11.0", "node": "v20.10.0"},
        "container": {"is_container": False, "indicators": []},
        "recommendation": {
            "suggested_asr_model": "large-v3",
            "suggested_diarization": "pyannote",
            "basis": ["mock"],
        },
    }


def test_probe_service_caches(monkeypatch):
    """Ensure the service caches results until refreshed."""
    calls = {"count": 0}

    def fake_probe():
        calls["count"] += 1
        return _mock_payload()

    monkeypatch.setattr("app.services.system_probe.build_probe_payload", fake_probe)

    first = SystemProbeService.get_cached_probe()
    second = SystemProbeService.get_cached_probe()
    assert first == second
    assert calls["count"] == 1

    refreshed = SystemProbeService.refresh_probe()
    assert refreshed == _mock_payload()
    assert calls["count"] == 2


class TestSystemRoutes:
    """Tests for /system routes using mocked payloads."""

    @pytest.fixture(autouse=True)
    def override_auth(self):
        app.dependency_overrides[get_current_user] = lambda: User(
            id=1, username="admin", email="admin@selenite.local"
        )
        yield
        app.dependency_overrides.pop(get_current_user, None)

    async def test_get_system_info(self, monkeypatch):
        """GET /system/info returns cached data."""
        monkeypatch.setattr(SystemProbeService, "get_cached_probe", lambda: _mock_payload())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/system/info")
        assert response.status_code == 200
        payload = response.json()
        assert payload["os"]["system"] == "TestOS"
        assert payload["gpu"]["has_gpu"] is True

    async def test_refresh_system_info(self, monkeypatch):
        """POST /system/info/detect refreshes data."""
        monkeypatch.setattr(SystemProbeService, "refresh_probe", lambda: _mock_payload())
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/system/info/detect")
        assert response.status_code == 200
        payload = response.json()
        assert payload["recommendation"]["suggested_asr_model"] == "large-v3"
