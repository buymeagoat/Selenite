"""Pydantic models for system probe responses."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OSInfo(BaseModel):
    system: str
    release: str
    version: str
    machine: str


class CPUInfo(BaseModel):
    model: Optional[str]
    architecture: Optional[str]
    cores_physical: Optional[int]
    cores_logical: Optional[int]
    max_frequency_mhz: Optional[float]


class MemoryInfo(BaseModel):
    total_gb: Optional[float]
    available_gb: Optional[float]


class GPUDevice(BaseModel):
    name: Optional[str]
    memory_gb: Optional[float]
    multi_processor_count: Optional[int]


class GPUInfo(BaseModel):
    has_gpu: bool
    api: Optional[str]
    driver: Optional[str]
    devices: List[GPUDevice]


class DiskUsage(BaseModel):
    path: str
    total_gb: Optional[float]
    used_gb: Optional[float]
    free_gb: Optional[float]


class StorageInfo(BaseModel):
    database: Optional[DiskUsage] = None
    media: DiskUsage
    transcripts: DiskUsage
    project: DiskUsage


class NetworkInterface(BaseModel):
    name: str
    ipv4: List[str]


class NetworkInfo(BaseModel):
    hostname: str
    interfaces: List[NetworkInterface]


class RuntimeInfo(BaseModel):
    python: str
    node: Optional[str]


class ContainerInfo(BaseModel):
    is_container: bool = Field(..., alias="is_container")
    indicators: List[str]

    model_config = {"populate_by_name": True}


class RecommendationInfo(BaseModel):
    suggested_asr_model: str
    suggested_diarization: str
    basis: List[str]


class SystemProbeResponse(BaseModel):
    detected_at: datetime
    os: OSInfo
    cpu: CPUInfo
    memory: MemoryInfo
    gpu: GPUInfo
    storage: StorageInfo
    network: NetworkInfo
    runtime: RuntimeInfo
    container: ContainerInfo
    recommendation: RecommendationInfo
