"""Unit tests for export service helpers to raise coverage."""

from types import SimpleNamespace

from app.services.export_service import ExportService


class DummyJob(SimpleNamespace):
    """Lightweight object that mimics the fields ExportService reads."""


def build_job(**overrides):
    base = {
        "id": "job-123",
        "original_filename": "sample.wav",
        "created_at": None,
        "duration": 42.5,
        "language_detected": "en",
        "model_used": "small",
        "speaker_count": 1,
    }
    base.update(overrides)
    return DummyJob(**base)


def sample_segments():
    return [
        {"start": 0.0, "end": 1.5, "text": "Hello"},
        {"start": 1.5, "end": 3.0, "text": "World"},
    ]


def sample_transcript():
    return {
        "job_id": "job-123",
        "text": "Hello World",
        "segments": sample_segments(),
        "language": "en",
        "duration": 3.0,
    }


def test_export_txt_bytes():
    job = build_job()
    result = ExportService.export_txt(job, "hello")
    assert result == b"hello"


def test_export_json_contains_metadata():
    job = build_job()
    payload = sample_transcript()
    data = ExportService.export_json(job, payload)
    assert b"job-123" in data
    assert b"segments" in data


def test_export_srt_structure():
    job = build_job()
    output = ExportService.export_srt(job, sample_segments())
    text = output.decode()
    assert "1" in text and "2" in text
    assert "-->" in text


def test_export_vtt_structure():
    job = build_job()
    output = ExportService.export_vtt(job, sample_segments())
    text = output.decode()
    assert "WEBVTT" in text
    assert "Hello" in text


def test_export_md_contains_sections():
    job = build_job()
    text = ExportService.export_md(job, "Hello", sample_segments()).decode()
    assert "# sample.wav" in text
    assert "## Transcript" in text


def test_export_docx_generates_bytes():
    job = build_job()
    content = ExportService.export_docx(job, "Hello", sample_segments())
    assert len(content) > 0
