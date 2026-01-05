"""Tests for the model registry admin routes."""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import BACKEND_ROOT
from app.database import AsyncSessionLocal, Base, engine
from app.main import app
from app.models.user import User
from app.utils.security import create_access_token, hash_password

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="function")
async def test_db():
    """Initialize a clean database with admin and regular users."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        admin = User(
            username="admin",
            email="admin@selenite.local",
            hashed_password=hash_password("pass1234"),
            is_admin=True,
        )
        user = User(
            username="member",
            email="member@example.com",
            hashed_password=hash_password("pass1234"),
        )
        session.add_all([admin, user])
        await session.commit()

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def admin_headers(test_db):
    token = create_access_token({"user_id": 1, "username": "admin"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user_headers(test_db):
    token = create_access_token({"user_id": 2, "username": "member"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def model_path_factory(tmp_path):
    """Create throwaway files inside backend/models for weight registration."""

    created: list[Path] = []
    models_root = BACKEND_ROOT / "models"

    def factory(relative: str) -> str:
        target = models_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok", encoding="utf-8")
        created.append(target)
        return str(target.resolve())

    yield factory

    for path in created:
        try:
            path.unlink()
        except FileNotFoundError:
            pass


@pytest.fixture
def set_path_factory():
    """Create throwaway directories inside backend/models for set registration."""

    created: list[Path] = []
    models_root = BACKEND_ROOT / "models"

    def factory(relative: str) -> str:
        target = models_root / relative
        target.mkdir(parents=True, exist_ok=True)
        created.append(target)
        return str(target.resolve())

    yield factory

    for path in sorted(created, key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


async def test_create_model_set_success(test_db, admin_headers, set_path_factory):
    payload = {
        "type": "asr",
        "name": "VOSK",
        "description": "Offline friendly",
        "abs_path": set_path_factory("vosk"),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/models/providers", json=payload, headers=admin_headers)

    assert response.status_code == 201
    body = response.json()
    assert body["enabled"] is True
    assert body["type"] == "asr"
    assert body["name"] == "vosk"  # normalized
    assert body["abs_path"].startswith(str((BACKEND_ROOT / "models").resolve()))


async def test_create_model_weight_requires_admin(
    test_db, admin_headers, user_headers, model_path_factory, set_path_factory
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        set_payload = {
            "type": "asr",
            "name": "custom",
            "abs_path": set_path_factory("custom"),
        }
        created = await client.post("/models/providers", json=set_payload, headers=admin_headers)
        set_id = created.json()["id"]

        weight_payload = {
            "name": "alpha",
            "description": "alpha model",
            "abs_path": model_path_factory("custom/alpha/model.bin"),
        }
        response = await client.post(
            f"/models/providers/{set_id}/weights", json=weight_payload, headers=user_headers
        )

    assert response.status_code == 403


async def test_duplicate_set_names_rejected(test_db, admin_headers, set_path_factory):
    payload = {
        "type": "asr",
        "name": "nemo",
        "abs_path": set_path_factory("nemo"),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/models/providers", json=payload, headers=admin_headers)
        assert first.status_code == 201
        dup = await client.post("/models/providers", json=payload, headers=admin_headers)

    assert dup.status_code == 409


async def test_weight_disable_requires_reason(
    test_db, admin_headers, model_path_factory, set_path_factory
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        set_payload = {
            "type": "asr",
            "name": "speechbrain",
            "abs_path": set_path_factory("speechbrain"),
        }
        created = await client.post("/models/providers", json=set_payload, headers=admin_headers)
        set_id = created.json()["id"]

        weight_payload = {
            "name": "sb-medium",
            "description": "SpeechBrain Medium",
            "abs_path": model_path_factory("speechbrain/sb-medium/model.bin"),
        }
        weight_resp = await client.post(
            f"/models/providers/{set_id}/weights", json=weight_payload, headers=admin_headers
        )
        weight_id = weight_resp.json()["id"]

        bad_patch = await client.patch(
            f"/models/providers/weights/{weight_id}",
            json={"enabled": False},
            headers=admin_headers,
        )
        assert bad_patch.status_code == 400

        good_patch = await client.patch(
            f"/models/providers/weights/{weight_id}",
            json={"enabled": False, "disable_reason": "GPU offline"},
            headers=admin_headers,
        )
        assert good_patch.status_code == 200
        body = good_patch.json()
        assert body["enabled"] is False
        assert body["disable_reason"] == "GPU offline"
        assert body["has_weights"] is True


async def test_enable_empty_weights_setting_allows_missing_files(
    test_db, admin_headers, set_path_factory
):
    weight_dir = BACKEND_ROOT / "models" / "force-test" / "empty-weight"
    weight_dir.mkdir(parents=True, exist_ok=True)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            set_payload = {
                "type": "asr",
                "name": "force-test",
                "abs_path": set_path_factory("force-test"),
            }
            created = await client.post(
                "/models/providers", json=set_payload, headers=admin_headers
            )
            set_id = created.json()["id"]

            weight_payload = {
                "name": "empty-weight",
                "description": "Empty dir",
                "abs_path": str(weight_dir.resolve()),
            }
            weight_resp = await client.post(
                f"/models/providers/{set_id}/weights", json=weight_payload, headers=admin_headers
            )
            weight_id = weight_resp.json()["id"]

            blocked = await client.patch(
                f"/models/providers/weights/{weight_id}",
                json={"enabled": True},
                headers=admin_headers,
            )
            assert blocked.status_code == 400

            enable_setting = await client.put(
                "/settings",
                json={"enable_empty_weights": True},
                headers=admin_headers,
            )
            assert enable_setting.status_code == 200

            allowed = await client.patch(
                f"/models/providers/weights/{weight_id}",
                json={"enabled": True},
                headers=admin_headers,
            )
            assert allowed.status_code == 200
            assert allowed.json()["enabled"] is True
    finally:
        try:
            weight_dir.rmdir()
        except OSError:
            pass


async def test_list_returns_sets_with_weights(
    test_db, admin_headers, model_path_factory, set_path_factory
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        set_payloads = [
            {"type": "asr", "name": "vosk", "abs_path": set_path_factory("vosk")},
            {"type": "diarizer", "name": "pyannote", "abs_path": set_path_factory("pyannote")},
        ]
        created_set_ids = []
        for payload in set_payloads:
            resp = await client.post("/models/providers", json=payload, headers=admin_headers)
            created_set_ids.append(resp.json()["id"])

        weight_payloads = [
            {
                "name": "vosk-en",
                "description": "Vosk English",
                "abs_path": model_path_factory("vosk/en/model.bin"),
            },
            {
                "name": "pyannote-core",
                "description": "Pyannote Core",
                "abs_path": model_path_factory("pyannote/core/model.bin"),
            },
        ]

        for set_id, weight_payload in zip(created_set_ids, weight_payloads):
            resp = await client.post(
                f"/models/providers/{set_id}/weights", json=weight_payload, headers=admin_headers
            )
            assert resp.status_code == 201

        listing = await client.get("/models/providers", headers=admin_headers)

    assert listing.status_code == 200
    data = listing.json()
    assert len(data) == 2
    for item in data:
        assert "weights" in item
        assert len(item["weights"]) == 1
        assert item["weights"][0]["abs_path"].startswith(str((BACKEND_ROOT / "models").resolve()))
        assert item["weights"][0]["has_weights"] is True


async def test_non_admin_list_filters_disabled_sets_and_weights(
    test_db, admin_headers, user_headers, model_path_factory, set_path_factory
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        enabled_set = await client.post(
            "/models/providers",
            json={"type": "asr", "name": "whisper", "abs_path": set_path_factory("whisper")},
            headers=admin_headers,
        )
        enabled_set_id = enabled_set.json()["id"]
        disabled_set = await client.post(
            "/models/providers",
            json={"type": "asr", "name": "kaldi", "abs_path": set_path_factory("kaldi")},
            headers=admin_headers,
        )
        disabled_set_id = disabled_set.json()["id"]

        enabled_weight = await client.post(
            f"/models/providers/{enabled_set_id}/weights",
            json={
                "name": "tiny",
                "description": "Tiny",
                "abs_path": model_path_factory("whisper/tiny/model.bin"),
            },
            headers=admin_headers,
        )
        enabled_weight_id = enabled_weight.json()["id"]
        disabled_weight = await client.post(
            f"/models/providers/{enabled_set_id}/weights",
            json={
                "name": "large",
                "description": "Large",
                "abs_path": model_path_factory("whisper/large/model.bin"),
            },
            headers=admin_headers,
        )
        disabled_weight_id = disabled_weight.json()["id"]

        await client.patch(
            f"/models/providers/weights/{disabled_weight_id}",
            json={"enabled": False, "disable_reason": "disabled"},
            headers=admin_headers,
        )
        await client.patch(
            f"/models/providers/{disabled_set_id}",
            json={"enabled": False, "disable_reason": "disabled"},
            headers=admin_headers,
        )

        listing = await client.get("/models/providers", headers=user_headers)

    assert listing.status_code == 200
    data = listing.json()
    assert len(data) == 1
    assert data[0]["name"] == "whisper"
    assert len(data[0]["weights"]) == 1
    assert data[0]["weights"][0]["id"] == enabled_weight_id


async def test_weight_file_path_validation(
    test_db, admin_headers, model_path_factory, set_path_factory
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        set_payload = {"type": "asr", "name": "kaldi", "abs_path": set_path_factory("kaldi")}
        created = await client.post("/models/providers", json=set_payload, headers=admin_headers)
        set_id = created.json()["id"]

        bad_payload = {
            "name": "kaldi-weight",
            "description": "Kaldi Weight",
            "abs_path": "../outside/model.bin",
        }
        bad_resp = await client.post(
            f"/models/providers/{set_id}/weights", json=bad_payload, headers=admin_headers
        )
        assert bad_resp.status_code == 400

        outside_set_payload = {
            "name": "kaldi-weight-outside",
            "description": "Kaldi Weight Outside",
            "abs_path": model_path_factory("other/kaldi/model.bin"),
        }
        outside_set_resp = await client.post(
            f"/models/providers/{set_id}/weights", json=outside_set_payload, headers=admin_headers
        )
        assert outside_set_resp.status_code == 400

        good_payload = {
            "name": "kaldi-weight-valid",
            "description": "Kaldi Weight",
            "abs_path": model_path_factory("kaldi/weight/model.bin"),
        }
        good_resp = await client.post(
            f"/models/providers/{set_id}/weights", json=good_payload, headers=admin_headers
        )
        assert good_resp.status_code == 201


async def test_delete_weight_and_set_cascade(
    test_db, admin_headers, model_path_factory, set_path_factory
):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        set_payload = {"type": "asr", "name": "kaldi", "abs_path": set_path_factory("kaldi")}
        created = await client.post("/models/providers", json=set_payload, headers=admin_headers)
        set_id = created.json()["id"]

        weight_payload = {
            "name": "kaldi-weight",
            "description": "Kaldi Weight",
            "abs_path": model_path_factory("kaldi/weight/model.bin"),
        }
        weight_resp = await client.post(
            f"/models/providers/{set_id}/weights", json=weight_payload, headers=admin_headers
        )
        weight_id = weight_resp.json()["id"]

        delete_weight = await client.delete(
            f"/models/providers/weights/{weight_id}", headers=admin_headers
        )
        assert delete_weight.status_code == 204

        delete_set = await client.delete(f"/models/providers/{set_id}", headers=admin_headers)
        assert delete_set.status_code == 204

        # Verify listing is empty
        listing = await client.get("/models/providers", headers=admin_headers)
        assert listing.status_code == 200
        assert listing.json() == []
