"""Strict input and output contracts for the evidence-bound Data Architect."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from contracts import DataPolicy


class SourceFacts(BaseModel):
    """Machine-measured data facts. An LLM cannot supply the reference values."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_rows: int = Field(ge=0)
    transaction_rows: int = Field(ge=0)
    repeated_header_rows: int = Field(ge=0)
    total_control_rows: int = Field(ge=0)
    exact_duplicate_extra_rows: int = Field(ge=0)
    missing_unit_price_rows: int = Field(ge=0)
    blank_discount_rows: int = Field(ge=0)
    negative_quantity_rows: int = Field(ge=0)
    noncanonical_region_rows: int = Field(ge=0)
    comma_price_rows: int = Field(ge=0)
    spaced_quantity_rows: int = Field(ge=0)
    raw_quantity_total: int
    raw_discount_total: str = Field(pattern=r"^-?\d+\.\d{2}$")
    control_quantity: int
    control_discount: str = Field(pattern=r"^-?\d+\.\d{2}$")
    control_reconciled: bool


RequirementKey = Literal[
    "virtual_column", "invalid_expressions", "source_cleaning",
    "revenue_formula", "regional_aggregation", "tests_and_readme",
]
DecisionKey = Literal[
    "source_control", "duplicates", "negative_quantity",
    "missing_unit_price", "missing_discount", "region",
]
EvidenceKey = Literal[
    "task_spec", "original_tests", "source_profile",
    "source_controls", "inspected_orders", "approved_policy",
]


class Requirement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: RequirementKey
    implementation_expectation: str = Field(min_length=16, max_length=450)
    evidence_refs: list[EvidenceKey] = Field(min_length=1, max_length=3)


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: DecisionKey
    proposed_value: str = Field(min_length=2, max_length=120)
    classification: Literal["specified", "business_assumption", "data_integrity", "repair_policy"]
    justification: str = Field(min_length=24, max_length=650)
    risk: str = Field(min_length=12, max_length=650)
    evidence_refs: list[EvidenceKey] = Field(min_length=1, max_length=5)


class ArchitectReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    role: Literal["data_architect"]
    task_spec_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    summary: str = Field(min_length=30, max_length=1100)
    requirements: list[Requirement] = Field(min_length=6, max_length=10)
    observed_facts: SourceFacts
    proposed_policy: DataPolicy
    decisions: list[PolicyDecision] = Field(min_length=6, max_length=12)
    unresolved_business_questions: list[str] = Field(min_length=3, max_length=8)
    suggested_validation_cases: list[str] = Field(min_length=4, max_length=12)


class ArchitectGateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    status: Literal["APPROVED_FOR_ENGINEERING", "AWAITING_HUMAN_APPROVAL", "INCOMPLETE"]
    report_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    task_spec_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    verified_tool_calls: list[str]
    policy_diff: dict[str, dict[str, str]] = Field(default_factory=dict)
    failures: list[str] = Field(default_factory=list)
