# API Contract Specifications

Complete specification for all API endpoints in Selenite. These contracts must be implemented exactly as specified.

## Base URL
```
http://localhost:8100
```

## Authentication
All endpoints except `/auth/login` and `/health` require JWT Bearer token:
```
Authorization: Bearer <token>
```

---

## Authentication Endpoints

### POST /auth/login
**Description**: Authenticate user and receive JWT token

**Request**:
```json
{
  "username": "string (required, 3-50 chars)",
  "password": "string (required, 8-128 chars)"
}
```

**Response 200 OK**:
```json
{
  "access_token": "string (JWT token)",
  "token_type": "bearer",
  "expires_in": 86400
}
```

**Response 401 Unauthorized**:
```json
{
  "detail": "Incorrect username or password"
}
```

**Response 422 Validation Error**:
```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

---

### POST /auth/logout
**Description**: Invalidate current JWT token (optional, for token blacklist)

**Request**: None (token in header)

**Response 200 OK**:
```json
{
  "message": "Successfully logged out"
}
```

**Response 401 Unauthorized**:
```json
{
  "detail": "Invalid or expired token"
}
```

---

### GET /auth/me
**Description**: Get current authenticated user information

**Response 200 OK**:
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "created_at": "2025-11-15T10:00:00Z"
}
```

---

### POST /auth/change-password
**Description**: Change password for current user

**Request**:
```json
{
  "current_password": "string (required)",
  "new_password": "string (required, 8-128 chars)"
}
```

**Response 200 OK**:
```json
{
  "message": "Password updated successfully"
}
```

**Response 400 Bad Request**:
```json
{
  "detail": "Current password is incorrect"
}
```

---

## Job Management Endpoints

### GET /jobs
**Description**: List all jobs with optional filtering, searching, and pagination

**Query Parameters**:
- `status` (optional): Filter by status (queued, processing, completed, failed)
- `date_from` (optional): ISO-8601 date string (inclusive)
- `date_to` (optional): ISO-8601 date string (inclusive)
- `tags` (optional): Comma-separated tag IDs (e.g., "1,3,5")
- `search` (optional): Search term for filename or transcript content
- `limit` (optional, default: 50): Number of results per page
- `offset` (optional, default: 0): Pagination offset

**Response 200 OK**:
```json
{
  "total": 156,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "original_filename": "interview.mp3",
      "file_size": 15728640,
      "mime_type": "audio/mpeg",
      "duration": 1834.5,
      "status": "completed",
      "progress_percent": 100,
      "progress_stage": null,
      "estimated_time_left": null,
      "estimated_total_seconds": 1900,
      "model_used": "medium",
      "language_detected": "en",
      "speaker_count": 2,
      "has_timestamps": true,
      "has_speaker_labels": true,
      "tags": [
        {
          "id": 1,
          "name": "interviews",
          "color": "#2D6A4F"
        }
      ],
      "created_at": "2025-11-15T10:30:00Z",
      "updated_at": "2025-11-15T10:45:30Z",
      "started_at": "2025-11-15T10:30:15Z",
      "completed_at": "2025-11-15T10:45:30Z",
      "stalled_at": null
    }
  ]
}
```

---

### GET /jobs/{job_id}
**Description**: Get detailed information about a specific job

**Path Parameters**:
- `job_id` (required): UUID of the job

**Response 200 OK**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "interview.mp3",
  "saved_filename": "550e8400-e29b-41d4-a716-446655440000.mp3",
  "file_path": "/storage/media/550e8400-e29b-41d4-a716-446655440000.mp3",
  "file_size": 15728640,
  "mime_type": "audio/mpeg",
  "duration": 1834.5,
  "status": "completed",
  "progress_percent": 100,
  "progress_stage": null,
  "estimated_time_left": null,
  "estimated_total_seconds": 1900,
  "model_used": "medium",
  "language_detected": "en",
  "speaker_count": 2,
  "has_timestamps": true,
  "has_speaker_labels": true,
  "transcript_path": "/storage/transcripts/550e8400-e29b-41d4-a716-446655440000.txt",
  "error_message": null,
  "tags": [
    {
      "id": 1,
      "name": "interviews",
      "color": "#2D6A4F"
    }
  ],
  "available_exports": ["txt", "md", "srt", "vtt", "json", "docx"],
  "created_at": "2025-11-15T10:30:00Z",
  "updated_at": "2025-11-15T10:45:30Z",
  "started_at": "2025-11-15T10:30:15Z",
  "completed_at": "2025-11-15T10:45:30Z",
  "stalled_at": null
}
```

**Response 404 Not Found**:
```json
{
  "detail": "Job not found"
}
```

---

### POST /jobs
**Description**: Create new transcription job with file upload

**Request**:
- Content-Type: `multipart/form-data`
- Fields:
  - `file` (required): Audio or video file
  - `model` (optional, default: "medium"): Whisper model (tiny, base, small, medium, large)
  - `language` (optional, default: "auto"): Language code (en, es, fr, etc.) or "auto"
  - `enable_timestamps` (optional, default: true): Boolean
  - `enable_speaker_detection` (optional, default: true): Boolean

**Response 201 Created**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "original_filename": "lecture.mp4",
  "status": "queued",
  "created_at": "2025-11-15T11:00:00Z"
}
```

**Response 400 Bad Request**:
```json
{
  "detail": "Invalid file format. Supported formats: mp3, wav, m4a, flac, ogg, mp4, avi, mov, mkv"
}
```

**Response 413 Payload Too Large**:
```json
{
  "detail": "File size exceeds maximum allowed (2GB)"
}
```

---

### GET /jobs/{job_id}/status
**Description**: Get current status and progress for a job (optimized for polling)

**Path Parameters**:
- `job_id` (required): UUID of the job

**Response 200 OK**:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress_percent": 45,
  "progress_stage": "transcribing",
  "estimated_time_left": 420
}
```

---

### POST /jobs/{job_id}/cancel
**Description**: Cancel a queued or processing job

**Path Parameters**:
- `job_id` (required): UUID of the job

**Response 200 OK**:
```json
{
  "message": "Job cancelled successfully",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "cancelled"
}
```

**Response 400 Bad Request**:
```json
{
  "detail": "Cannot cancel job with status: completed"
}
```

---

### POST /jobs/{job_id}/restart
**Description**: Re-run transcription on existing file with new options

**Path Parameters**:
- `job_id` (required): UUID of the original job

**Request**:
```json
{
  "model": "large",
  "language": "auto",
  "enable_timestamps": true,
  "enable_speaker_detection": true
}
```

**Response 201 Created**:
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440000",
  "original_job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "created_at": "2025-11-15T12:00:00Z"
}
```

---

### DELETE /jobs/{job_id}
**Description**: Delete job and all associated files

**Path Parameters**:
- `job_id` (required): UUID of the job

**Response 200 OK**:
```json
{
  "message": "Job deleted successfully",
  "id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response 404 Not Found**:
```json
{
  "detail": "Job not found"
}
```

---

## Media & Transcript Endpoints

### GET /media/{job_id}
**Description**: Stream or download original audio/video file

**Path Parameters**:
- `job_id` (required): UUID of the job

**Query Parameters**:
- `download` (optional, default: false): If true, force download with Content-Disposition header

**Response 200 OK**:
- Content-Type: Appropriate MIME type (audio/mpeg, video/mp4, etc.)
- Content-Length: File size in bytes
- Body: File stream

**Response 206 Partial Content** (for range requests):
- Supports HTTP range requests for audio/video seeking

**Response 404 Not Found**:
```json
{
  "detail": "Media file not found"
}
```

---

### GET /transcripts/{job_id}
**Description**: Get primary transcript text

**Path Parameters**:
- `job_id` (required): UUID of the job

**Response 200 OK**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "Full transcript text here...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.5,
      "text": "Hello, this is the first segment.",
      "speaker": "SPEAKER_00"
    }
  ],
  "language": "en",
  "duration": 1834.5
}
```

**Response 404 Not Found**:
```json
{
  "detail": "Transcript not found. Job may not be completed."
}
```

---

### GET /transcripts/{job_id}/export
**Description**: Download transcript in specified format

**Path Parameters**:
- `job_id` (required): UUID of the job

**Query Parameters**:
- `format` (required): Export format (txt, md, srt, vtt, json, docx)

**Response 200 OK**:
- Content-Type: Appropriate MIME type based on format
  - txt: text/plain
  - md: text/markdown
  - srt: text/srt
  - vtt: text/vtt
  - json: application/json
  - docx: application/vnd.openxmlformats-officedocument.wordprocessingml.document
- Content-Disposition: attachment; filename="interview.{format}"
- Body: File content

**Response 400 Bad Request**:
```json
{
  "detail": "Invalid format. Supported: txt, md, srt, vtt, json, docx"
}
```

---

## Tag Management Endpoints

### GET /tags
**Description**: List all tags

**Response 200 OK**:
```json
{
  "total": 5,
  "items": [
    {
      "id": 1,
      "name": "interviews",
      "color": "#2D6A4F",
      "job_count": 12,
      "created_at": "2025-11-01T10:00:00Z"
    },
    {
      "id": 2,
      "name": "lectures",
      "color": "#40916C",
      "job_count": 8,
      "created_at": "2025-11-02T14:30:00Z"
    }
  ]
}
```

---

### POST /tags
**Description**: Create new tag

**Request**:
```json
{
  "name": "string (required, 1-50 chars, unique)",
  "color": "string (optional, hex color, default: auto-assigned)"
}
```

**Response 201 Created**:
```json
{
  "id": 6,
  "name": "meetings",
  "color": "#52B788",
  "job_count": 0,
  "created_at": "2025-11-15T12:00:00Z"
}
```

**Response 400 Bad Request**:
```json
{
  "detail": "Tag with name 'meetings' already exists"
}
```

---

### PUT /tags/{tag_id}
**Description**: Update tag (rename or change color)

**Path Parameters**:
- `tag_id` (required): ID of the tag

**Request**:
```json
{
  "name": "string (optional, 1-50 chars)",
  "color": "string (optional, hex color)"
}
```

**Response 200 OK**:
```json
{
  "id": 1,
  "name": "interviews-updated",
  "color": "#1B4332",
  "job_count": 12,
  "created_at": "2025-11-01T10:00:00Z"
}
```

---

### DELETE /tags/{tag_id}
**Description**: Delete tag (removes from all jobs)

**Path Parameters**:
- `tag_id` (required): ID of the tag

**Response 200 OK**:
```json
{
  "message": "Tag deleted successfully",
  "id": 1,
  "jobs_affected": 12
}
```

---

### POST /jobs/{job_id}/tags
**Description**: Assign tags to a job

**Path Parameters**:
- `job_id` (required): UUID of the job

**Request**:
```json
{
  "tag_ids": [1, 3, 5]
}
```

**Response 200 OK**:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tags": [
    {"id": 1, "name": "interviews", "color": "#2D6A4F"},
    {"id": 3, "name": "important", "color": "#40916C"},
    {"id": 5, "name": "archived", "color": "#52B788"}
  ]
}
```

---

### DELETE /jobs/{job_id}/tags/{tag_id}
**Description**: Remove tag from job

**Path Parameters**:
- `job_id` (required): UUID of the job
- `tag_id` (required): ID of the tag

**Response 200 OK**:
```json
{
  "message": "Tag removed from job",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "tag_id": 1
}
```

---

## Search Endpoint

### GET /search
**Description**: Full-text search across jobs

**Query Parameters**:
- `q` (required): Search query string
- `status` (optional): Filter by status
- `tags` (optional): Comma-separated tag IDs
- `date_from` (optional): ISO-8601 date
- `date_to` (optional): ISO-8601 date
- `limit` (optional, default: 50): Results per page
- `offset` (optional, default: 0): Pagination offset

**Response 200 OK**:
```json
{
  "query": "climate change",
  "total": 3,
  "items": [
    {
      "job_id": "550e8400-e29b-41d4-a716-446655440000",
      "original_filename": "climate-lecture.mp4",
      "status": "completed",
      "created_at": "2025-11-10T14:00:00Z",
      "matches": [
        {
          "type": "filename",
          "text": "climate-lecture.mp4",
          "highlight": "<mark>climate</mark>-lecture.mp4"
        },
        {
          "type": "transcript",
          "text": "...discussing climate change impacts...",
          "highlight": "...discussing <mark>climate change</mark> impacts..."
        }
      ]
    }
  ]
}
```

---

## Settings Endpoints

### GET /settings
**Description**: Get all user settings

**Response 200 OK**:
```json
{
  "default_model": "medium",
  "default_language": "auto",
  "default_timestamps": true,
  "default_speaker_detection": true,
  "max_concurrent_jobs": 3,
  "storage_location": "/storage",
  "storage_used_bytes": 15728640000,
  "storage_limit_bytes": 107374182400
}
```

---

### PUT /settings
**Description**: Update user settings

**Request**:
```json
{
  "default_model": "large",
  "default_language": "en",
  "default_timestamps": false,
  "default_speaker_detection": true,
  "max_concurrent_jobs": 5
}
```

**Response 200 OK**:
```json
{
  "message": "Settings updated successfully",
  "settings": {
    "default_model": "large",
    "default_language": "en",
    "default_timestamps": false,
    "default_speaker_detection": true,
    "max_concurrent_jobs": 5
  }
}
```

---

## System Endpoints

### GET /health
**Description**: Health check endpoint (no authentication required)

**Response 200 OK**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "timestamp": "2025-11-15T12:00:00Z"
}
```

---

### GET /models
**Description**: List available Whisper models

**Response 200 OK**:
```json
{
  "models": [
    {
      "name": "tiny",
      "size_mb": 75,
      "available": true,
      "path": "/models/tiny.pt"
    },
    {
      "name": "base",
      "size_mb": 142,
      "available": true,
      "path": "/models/base.pt"
    },
    {
      "name": "small",
      "size_mb": 466,
      "available": true,
      "path": "/models/small.pt"
    },
    {
      "name": "medium",
      "size_mb": 1464,
      "available": true,
      "path": "/models/medium.pt"
    },
    {
      "name": "large",
      "size_mb": 2886,
      "available": false,
      "path": "/models/large.pt"
    }
  ]
}
```

---

### POST /system/restart
**Description**: Restart the backend server (requires password confirmation)

**Request**:
```json
{
  "password": "string (required, current user password)"
}
```

**Response 200 OK**:
```json
{
  "message": "Server will restart in 3 seconds"
}
```

**Response 403 Forbidden**:
```json
{
  "detail": "Incorrect password"
}
```

---

### POST /system/shutdown
**Description**: Shutdown the backend server (requires password confirmation)

**Request**:
```json
{
  "password": "string (required, current user password)"
}
```

**Response 200 OK**:
```json
{
  "message": "Server will shutdown in 3 seconds"
}
```

**Response 403 Forbidden**:
```json
{
  "detail": "Incorrect password"
}
```

---

## Error Response Format

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Error description",
      "type": "error_type"
    }
  ]
}
```

---

## HTTP Status Codes

- `200 OK`: Successful GET, PUT, POST operation
- `201 Created`: Successful resource creation
- `204 No Content`: Successful DELETE operation
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Missing or invalid authentication
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `413 Payload Too Large`: File upload exceeds size limit
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server-side error

---

## Rate Limiting

- Login endpoint: 5 requests per minute per IP
- All other endpoints: 100 requests per minute per user

Rate limit headers:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1700050800
```

---

**These contracts are the source of truth for API implementation. Backend routes must match these specifications exactly.**

---
### E2E Testing Phase Note (Nov 17 2025)
Active smoke tests exercise `/auth/login`, `/jobs` (listing + creation). Upcoming E2E coverage will incorporate `/jobs/{job_id}/status`, tag endpoints (`/tags`, `/jobs/{job_id}/tags`), settings endpoints (`/settings`, `/auth/change-password`), and job control endpoints (`/jobs/{job_id}/cancel`, `/jobs/{job_id}/restart`). No contract changes have been introduced; this serves as a confirmation of spec stability entering broader end-to-end validation.
