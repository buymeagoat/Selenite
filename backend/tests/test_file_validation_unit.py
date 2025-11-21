"""Unit tests for file validation utilities."""

import io

import pytest
from fastapi import UploadFile, HTTPException

from app.utils import file_validation


def make_upload(data: bytes, name: str) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data))


@pytest.mark.asyncio
async def test_validate_media_file_extension_fallback(monkeypatch):
    """When magic is unavailable, extension map should be used."""
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", False)
    upload = make_upload(b"\x00\x11\x22", "sample.mp3")
    mime, size = await file_validation.validate_media_file(upload)
    assert mime == "audio/mpeg"
    assert size == 3


@pytest.mark.asyncio
async def test_validate_media_file_magic_allowed(monkeypatch):
    """Magic detection returning allowed MIME should pass."""
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", True)

    class FakeMagic:
        @staticmethod
        def from_buffer(buf, mime=True):
            return "audio/mpeg"

    monkeypatch.setattr(file_validation, "magic", FakeMagic(), raising=False)
    upload = make_upload(b"\x00" * 10, "whatever.bin")
    mime, _ = await file_validation.validate_media_file(upload)
    assert mime == "audio/mpeg"


@pytest.mark.asyncio
async def test_validate_media_file_magic_fallback(monkeypatch):
    """Magic returning unsupported type should fall back to extension detection."""
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", True)

    class FakeMagic:
        @staticmethod
        def from_buffer(buf, mime=True):
            return "text/plain"

    monkeypatch.setattr(file_validation, "magic", FakeMagic(), raising=False)
    upload = make_upload(b"\x00" * 10, "sample.mp3")
    mime, _ = await file_validation.validate_media_file(upload)
    assert mime == "audio/mpeg"


@pytest.mark.asyncio
async def test_validate_media_file_magic_exception(monkeypatch):
    """If magic raises, the exception path should be covered."""
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", True)

    class FakeMagic:
        @staticmethod
        def from_buffer(buf, mime=True):
            raise RuntimeError("bad magic")

    monkeypatch.setattr(file_validation, "magic", FakeMagic(), raising=False)
    upload = make_upload(b"\x00" * 10, "sample.mp3")
    mime, _ = await file_validation.validate_media_file(upload)
    assert mime == "audio/mpeg"


@pytest.mark.asyncio
async def test_validate_media_file_invalid_extension(monkeypatch):
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", False)
    upload = make_upload(b"\x00\x01", "unknown.xyz")
    with pytest.raises(HTTPException) as exc:
        await file_validation.validate_media_file(upload)
    assert exc.value.status_code == 400
    assert "Unable to determine file type" in exc.value.detail


@pytest.mark.asyncio
async def test_validate_media_file_invalid_detected_mime(monkeypatch):
    """Extension map returning unsupported MIME should raise."""
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", False)
    monkeypatch.setitem(file_validation.EXTENSION_MIME_MAP, ".mp3", "text/plain")
    upload = make_upload(b"\x00" * 10, "sample.mp3")
    with pytest.raises(HTTPException) as exc:
        await file_validation.validate_media_file(upload)
    assert "not supported" in exc.value.detail


@pytest.mark.asyncio
async def test_validate_media_file_empty_file(monkeypatch):
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", False)
    upload = make_upload(b"", "sample.mp3")
    with pytest.raises(HTTPException) as exc:
        await file_validation.validate_media_file(upload)
    assert exc.value.status_code == 400
    assert "Empty file" in exc.value.detail


@pytest.mark.asyncio
async def test_validate_media_file_too_large(monkeypatch):
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", False)
    monkeypatch.setattr(file_validation, "MAX_FILE_SIZE", 1024 * 1024)
    upload = make_upload(b"a" * (1024 * 1024 + 1), "sample.mp3")
    with pytest.raises(HTTPException) as exc:
        await file_validation.validate_media_file(upload)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_validate_media_file_path_traversal(monkeypatch):
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", False)
    upload = make_upload(b"\x01\x02", "../sample.mp3")
    with pytest.raises(HTTPException) as exc:
        await file_validation.validate_media_file(upload)
    assert exc.value.status_code == 400
    assert "path traversal" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_validate_media_file_invalid_filename(monkeypatch):
    monkeypatch.setattr(file_validation, "MAGIC_AVAILABLE", True)

    class FakeMagic:
        @staticmethod
        def from_buffer(buf, mime=True):
            return "audio/mpeg"

    monkeypatch.setattr(file_validation, "magic", FakeMagic(), raising=False)
    upload = make_upload(b"\x01\x02", ".")
    with pytest.raises(HTTPException) as exc:
        await file_validation.validate_media_file(upload)
    assert exc.value.status_code == 400
    assert "Invalid filename" in exc.value.detail
