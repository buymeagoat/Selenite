"""Tests for file validation."""

import pytest
from io import BytesIO
from fastapi import UploadFile, HTTPException
from app.utils.file_validation import validate_media_file


@pytest.mark.asyncio
async def test_validate_empty_file():
    """Test that empty files are rejected."""
    file = UploadFile(filename="test.mp3", file=BytesIO(b""))

    with pytest.raises(HTTPException) as exc_info:
        await validate_media_file(file)

    assert exc_info.value.status_code == 400
    assert "Empty file" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_file_extension_fallback():
    """Test extension-based validation when magic is unavailable."""
    # Create a fake audio file with some content
    content = b"fake audio data" * 100
    file = UploadFile(filename="test.mp3", file=BytesIO(content))

    # Should not raise - extension is valid
    mime_type, size = await validate_media_file(file)

    assert mime_type == "audio/mpeg"
    assert size == len(content)


@pytest.mark.asyncio
async def test_validate_invalid_extension():
    """Test that files with invalid extensions are rejected."""
    content = b"fake data" * 100
    file = UploadFile(filename="test.exe", file=BytesIO(content))

    with pytest.raises(HTTPException) as exc_info:
        await validate_media_file(file)

    assert exc_info.value.status_code == 400
    assert "Unable to determine file type" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_path_traversal_in_filename():
    """Test that path traversal attempts in filenames are rejected."""
    content = b"fake audio data" * 100
    file = UploadFile(filename="../../../etc/passwd.mp3", file=BytesIO(content))

    with pytest.raises(HTTPException) as exc_info:
        await validate_media_file(file)

    assert exc_info.value.status_code == 400
    assert "Invalid filename" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_supported_extensions():
    """Test that common media extensions are accepted."""
    extensions = [
        ("test.mp3", "audio/mpeg"),
        ("test.wav", "audio/wav"),
        ("test.mp4", "video/mp4"),
        ("test.flac", "audio/flac"),
    ]

    for filename, expected_mime in extensions:
        content = b"fake media data" * 100
        file = UploadFile(filename=filename, file=BytesIO(content))

        mime_type, size = await validate_media_file(file)

        assert mime_type == expected_mime
        assert size == len(content)
