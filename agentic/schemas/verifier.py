"""Typed, evidence-linked output for the independent adversarial Verification Engineer."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VerificationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    role: Literal["verification_engineer"]
    candidate_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    p3_receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    overall_assessment: str = Field(min_length=40, max_length=1300)
    tested_assumption: str = Field(min_length=30, max_length=500)
    expected_failure_mode: str = Field(min_length=30, max_length=500)
    original_test_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposed_test_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    risk_notes: list[str] = Field(min_length=2, max_length=12)
    next_action: Literal["request_independent_test", "request_rework"]
    unverified_assertions: list[str] = Field(default_factory=list, max_length=10)


class VerificationGate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["PENDING_ADVERSARIAL_EXECUTION", "INCOMPLETE"]
    candidate_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposed_test_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    verified_tool_calls: list[str]
    failures: list[str] = Field(default_factory=list)
