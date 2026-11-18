"""Persisted, evidence-linked agent proposals. An LLM cannot approve its own decision.

This is deliberately separate from the approved DataPolicy: proposed agent advice is
untrusted until a human explicitly reviews and commits a contract change.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import Literal

from .models import ReviewReport


class DataDecision(BaseModel):
    """Structured proposal, not an authorization to mutate source or code."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^DD-[0-9]{4}$")
    role: Literal["data_architect", "data_engineer", "verification_engineer"]
    target: Literal[
        "duplicates", "negative_quantities", "missing_prices", "regions",
        "source_controls", "quality_gate", "other",
    ]
    proposal: str = Field(min_length=15, max_length=500)
    evidence: str = Field(min_length=12, max_length=1000)
    risk: str = Field(min_length=10, max_length=500)
    status: Literal["pending_human_review"] = "pending_human_review"
    source_report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    approved_by: None = None

    @field_validator("approved_by")
    @classmethod
    def no_model_approval(cls, value: None) -> None:
        if value is not None:
            raise ValueError("Only an independently approved human policy change may authorize actions")
        return value


class DecisionLedger(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    reviewed_commit: str | None = None
    generated_at_utc: str
    source_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    approval_boundary: Literal["human_review_required"] = "human_review_required"
    decisions: list[DataDecision] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_decisions(self) -> "DecisionLedger":
        ids = [item.id for item in self.decisions]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate decision ids")
        return self


def create_ledger(manifest: dict) -> DecisionLedger:
    """Extract ONLY explicitly model-proposed decisions and attach original report hashes."""
    reports = [ReviewReport.model_validate(entry) for entry in manifest["agent_reviews"]]
    source_digest = hashlib.sha256(
        json.dumps(manifest["provenance"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    proposals: list[DataDecision] = []
    for report in reports:
        report_digest = hashlib.sha256(
            json.dumps(report.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        for item in report.decision_proposals:
            proposals.append(DataDecision(
                id=f"DD-{len(proposals)+1:04d}",
                role=report.role,
                target=item.target,
                proposal=item.proposal,
                evidence=item.evidence,
                risk=item.risk,
                source_report_sha256=report_digest,
            ))
    return DecisionLedger(
        reviewed_commit=manifest.get("git_revision"),
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        source_manifest_sha256=source_digest,
        decisions=proposals,
    )


def write_ledger_atomic(ledger: DecisionLedger, path: Path) -> None:
    """Use an atomic replace, never silently alter the immutable approved policy."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".data-decisions-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(ledger.model_dump_json(indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Write unapproved decisions with report-hash provenance")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    from .verify import verify_manifest

    manifest = json.loads(args.input.read_text(encoding="utf-8"))
    verify_manifest(manifest)
    ledger = create_ledger(manifest)
    write_ledger_atomic(ledger, args.output)
    print(f"Unapproved evidence-linked proposals: {len(ledger.decisions)}")


if __name__ == "__main__":
    main()
