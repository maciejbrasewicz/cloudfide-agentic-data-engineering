"""Schema for real Engineer writes. Textual claims alone never pass P2."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .architect import RequirementKey


class CandidateFileEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    path: str = Field(min_length=6, max_length=100)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    requirement_keys: list[RequirementKey] = Field(min_length=1, max_length=6)


class EngineerReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    role: Literal["data_engineer"]
    mode: Literal["rebuild", "improve"]
    architect_report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    summary: str = Field(min_length=25, max_length=1200)
    actual_files_written: list[CandidateFileEvidence] = Field(min_length=1, max_length=30)
    validation_requested: bool
    validation_claim: Literal["pending_independent_runner"] = "pending_independent_runner"
    known_limitations: list[str] = Field(default_factory=list, max_length=10)
