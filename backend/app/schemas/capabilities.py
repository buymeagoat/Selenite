"""Schemas for capability reporting."""

from typing import List

from pydantic import BaseModel


class ASRProvider(BaseModel):
    provider: str
    display_name: str
    available: bool
    models: List[str]
    notes: List[str] = []


class DiarizerOption(BaseModel):
    key: str
    display_name: str
    requires_gpu: bool
    available: bool
    notes: List[str] = []


class CapabilityResponse(BaseModel):
    asr: List[ASRProvider]
    diarizers: List[DiarizerOption]
