"""File handling utilities for media uploads and storage."""

import os
import uuid
from pathlib import Path
from typing import Tuple, Optional

from fastapi import UploadFile, HTTPException, status


# Supported file formats
AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
VIDEO_FORMATS = {".mp4", ".avi", ".mov", ".mkv"}
ALLOWED_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS

# MIME types mapping
MIME_TYPE_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".mp4": "video/mp4",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
}

# Maximum file size: 2GB
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB in bytes


def validate_file_format(filename: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if the file format is supported.

    Args:
        filename: Original filename with extension

    Returns:
        Tuple of (is_valid, error_message)
    """
    file_ext = Path(filename).suffix.lower()

    if file_ext not in ALLOWED_FORMATS:
        formats_str = ", ".join(sorted(ALLOWED_FORMATS))
        return False, f"Invalid file format. Supported formats: {formats_str}"

    return True, None


def validate_file_size(file_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate if the file size is within limits.

    Args:
        file_size: File size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    if file_size > MAX_FILE_SIZE:
        max_gb = MAX_FILE_SIZE / (1024 * 1024 * 1024)
        return False, f"File size exceeds maximum allowed ({max_gb}GB)"

    if file_size == 0:
        return False, "File is empty"

    return True, None


def get_mime_type(filename: str) -> str:
    """
    Get MIME type from filename extension.

    Args:
        filename: Original filename with extension

    Returns:
        MIME type string
    """
    file_ext = Path(filename).suffix.lower()
    return MIME_TYPE_MAP.get(file_ext, "application/octet-stream")


def generate_secure_filename(original_filename: str) -> Tuple[str, uuid.UUID]:
    """
    Generate a secure unique filename while preserving extension.

    Args:
        original_filename: Original filename from upload

    Returns:
        Tuple of (secure_filename, file_uuid)
    """
    file_ext = Path(original_filename).suffix.lower()
    file_uuid = uuid.uuid4()
    secure_filename = f"{file_uuid}{file_ext}"
    return secure_filename, file_uuid


async def save_uploaded_file(file: UploadFile, storage_path: str) -> Tuple[str, int, str]:
    """
    Save an uploaded file to storage directory.

    Args:
        file: FastAPI UploadFile object
        storage_path: Base storage directory path

    Returns:
        Tuple of (saved_file_path, file_size, mime_type)

    Raises:
        HTTPException: If validation fails or file cannot be saved
    """
    # Validate file format
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided",
        )

    is_valid, error_msg = validate_file_format(file.filename)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Generate secure filename
    secure_filename, file_uuid = generate_secure_filename(file.filename)
    file_path = os.path.join(storage_path, secure_filename)

    # Ensure storage directory exists
    os.makedirs(storage_path, exist_ok=True)

    # Read and validate file size
    file_content = await file.read()
    file_size = len(file_content)

    is_valid, error_msg = validate_file_size(file_size)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=error_msg,
        )

    # Save file
    try:
        with open(file_path, "wb") as f:
            f.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}",
        )

    mime_type = get_mime_type(file.filename)

    return file_path, file_size, mime_type
