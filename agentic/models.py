"""Strict machine-readable model output; all findings are untrusted until verified."""
from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


_CATEGORY_ALIASES = {
    "implementation": "pipeline",
    "code": "pipeline",
    "output": "pipeline",
    "tests": "testing",
    "test": "testing",
    "policy": "spec",
    "requirements": "spec",
    "data": "source_data",
    "data_quality": "source_data",
}


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["spec", "source_data", "pipeline", "security", "testing", "documentation"]
    severity: Literal["low", "medium", "high"]
    statement: str = Field(min_length=12, max_length=500)
    evidence: str = Field(min_length=8, max_length=1000)
    suggested_verification: str = Field(min_length=5, max_length=500)

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: object) -> object:
        # Only explicitly recognized lexical synonyms may cross the boundary.
        # Other values remain invalid, rather than being silently accepted.
        if isinstance(value, str):
            normalized = value.strip().casefold()
            return _CATEGORY_ALIASES.get(normalized, normalized)
        return value


class ReviewReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["data_architect", "data_engineer", "verification_engineer"]
    summary: str = Field(min_length=10, max_length=1000)
    findings: list[Finding] = Field(default_factory=list, max_length=12)
    recommended_next_action: str = Field(min_length=5, max_length=600)


def parse_report(text: str) -> ReviewReport:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return ReviewReport.model_validate(json.loads(candidate))
