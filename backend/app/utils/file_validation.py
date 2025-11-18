"""File validation utilities for secure upload handling."""

try:
    import magic

    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    # python-magic or libmagic not available
    MAGIC_AVAILABLE = False

from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException, status


# Allowed MIME types for media files
ALLOWED_MIME_TYPES = {
    # Audio formats
    "audio/mpeg",  # MP3
    "audio/mp3",
    "audio/wav",  # WAV
    "audio/x-wav",
    "audio/wave",
    "audio/x-pn-wav",
    "audio/flac",  # FLAC
    "audio/x-flac",
    "audio/aac",  # AAC
    "audio/aacp",
    "audio/ogg",  # OGG
    "audio/opus",  # Opus
    "audio/webm",  # WebM audio
    "audio/m4a",  # M4A
    "audio/x-m4a",
    # Video formats
    "video/mp4",  # MP4
    "video/mpeg",  # MPEG
    "video/x-msvideo",  # AVI
    "video/avi",
    "video/quicktime",  # MOV
    "video/x-matroska",  # MKV
    "video/webm",  # WebM
    "video/ogg",  # OGG video
    "video/x-flv",  # FLV
    "video/3gpp",  # 3GP
    "video/3gpp2",  # 3G2
}

# Maximum file size: 2GB
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024

# File extensions to MIME type mapping (fallback)
EXTENSION_MIME_MAP = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".m4a": "audio/m4a",
    ".mp4": "video/mp4",
    ".mpeg": "video/mpeg",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".flv": "video/x-flv",
    ".3gp": "video/3gpp",
}


async def validate_media_file(file: UploadFile) -> Tuple[str, int]:
    """
    Validate uploaded media file for security and format compliance.

    Args:
        file: Uploaded file from FastAPI

    Returns:
        Tuple of (validated_mime_type, file_size)

    Raises:
        HTTPException: If file is invalid or insecure
    """
    # Check file size by reading in chunks
    file_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    file_content = bytearray()

    # Read first chunk for magic byte detection
    first_chunk = await file.read(chunk_size)
    file_content.extend(first_chunk)
    file_size += len(first_chunk)

    if file_size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file uploaded")

    # Continue reading to get total size (up to limit)
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        file_size += len(chunk)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size is {MAX_FILE_SIZE / (1024**3):.1f}GB",
            )

    # Reset file pointer for later use
    await file.seek(0)

    # Validate MIME type using magic bytes (more secure than extension)
    detected_mime = None
    if MAGIC_AVAILABLE:
        try:
            detected_mime = magic.from_buffer(bytes(file_content[:2048]), mime=True)
        except Exception:
            # Magic detection failed, fall back to extension
            pass

    if not detected_mime:
        # Fallback to extension-based detection
        extension = Path(file.filename or "").suffix.lower()
        detected_mime = EXTENSION_MIME_MAP.get(extension)

        if not detected_mime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to determine file type. Please ensure file has correct extension.",
            )

    # Check if MIME type is allowed
    if detected_mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{detected_mime}' not supported. "
            f"Supported formats: audio (MP3, WAV, FLAC, AAC, OGG, Opus, M4A) "
            f"and video (MP4, AVI, MOV, MKV, WebM, etc.)",
        )

    # Validate filename for path traversal attempts
    if file.filename:
        # Check for path traversal characters before sanitization
        if any(char in file.filename for char in ["../", "..\\", "\0", "/"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid filename: path traversal attempt detected",
            )

        filename = Path(file.filename).name  # Get just the filename, strip any path
        if not filename or filename == "." or filename == "..":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid filename")

    return detected_mime, file_size
