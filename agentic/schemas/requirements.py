"""Input evidence contract; contains fingerprints, never the original task text."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


_HASH = r"^[a-f0-9]{64}$"


class InputManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    mode: Literal["rebuild", "improve"]
    specification_sha256: str = Field(pattern=_HASH)
    source_csv_sha256: str = Field(pattern=_HASH)
    original_tests_sha256: str = Field(pattern=_HASH)
    approved_policy_sha256: str = Field(pattern=_HASH)
    base_commit: str = Field(pattern=r"^[a-f0-9]{40}$")
    run_id: str | None = Field(default=None, max_length=128)
    model_deployment: str = Field(min_length=1, max_length=128)
