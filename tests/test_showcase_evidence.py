"""Verify the public showcase is grounded in actual committed ETL evidence."""
from __future__ import annotations

import json
from decimal import Decimal

from pipeline import ROOT


SHOWCASE = ROOT / "showcase"
EVIDENCE = SHOWCASE / "data" / "evidence.json"


def _read():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_public_evidence_matches_deterministic_audit():
    evidence = _read()
    audit = json.loads((ROOT / "reports/data_quality.json").read_text(encoding="utf-8"))
    q = evidence["quality"]
    assert evidence["schemaVersion"] == 1
    for public_name, audit_name in (
        ("sourceRows", "source_rows"),
        ("cleanRows", "transactions_after_dedup"),
        ("exactDuplicates", "exact_duplicates_removed"),
        ("recoveredPrices", "missing_unit_prices_recovered"),
        ("negativeQuantities", "negative_quantities_retained"),
        ("controlQuantity", "raw_control_quantity"),
    ):
        assert q[public_name] == audit[audit_name]
    assert Decimal(q["netRevenue"]) == Decimal(audit["net_revenue"])
    assert Decimal(q["controlDiscount"]) == Decimal(audit["raw_control_discount"])
    assert q["reconciliation"] == "passed"


def test_public_hashes_match_audited_input_output_and_policy():
    evidence = _read()
    audit = json.loads((ROOT / "reports/data_quality.json").read_text(encoding="utf-8"))
    p = evidence["provenance"]
    assert p["sourceSha256"] == audit["source_sha256"]
    assert p["outputSha256"] == audit["output_sha256"]
    assert p["policySha256"] == audit["policy_sha256"]
    assert len(p["reviewedCommit"]) == 40
    assert len(p["publishedCommit"]) == 40


def test_region_totals_are_exactly_the_committed_csv():
    import csv
    with (ROOT / "revenue_by_region.csv").open(encoding="utf-8", newline="") as source:
        actual = {line["region"]: Decimal(line["revenue"]) for line in csv.DictReader(source)}
    q = _read()["quality"]
    displayed = {line["name"]: Decimal(str(line["value"])) for line in q["regions"]}
    assert displayed == actual
    assert sum(displayed.values(), Decimal(0)) == Decimal(q["netRevenue"])


def test_public_claims_do_not_invent_telemetry():
    evidence = _read()
    telemetry = evidence["observability"]
    assert telemetry["mode"] == "recorded_evidence"
    assert telemetry["traceStatus"] == "measured_tool_calls"
    assert telemetry["toolSpanCount"] == 16
    assert telemetry["wallDurationMs"] == 90802.312
    assert telemetry["otelExporterConfigured"] is False
    for field in ("traceId", "tokenUsage", "estimatedCost"):
        assert telemetry[field] is None
    assert len(evidence["agents"]) == 3
    assert [a["role"] for a in evidence["agents"]] == [
        "data_architect", "data_engineer", "verification_engineer"
    ]
    assert evidence["quality"]["testCount"] >= 64
    assert all(c["url"].startswith(evidence["provenance"]["repoUrl"] + "/pull/") for c in evidence["cases"])


def test_showcase_has_six_sections_and_only_local_js():
    html = (SHOWCASE / "index.html").read_text(encoding="utf-8")
    for page in ("overview", "architecture", "cases", "execution", "data", "evidence"):
        assert f'data-section="{page}"' in html
    assert '<script src="./app.js" defer>' in html
    assert len(_read()["decisions"]) >= 5
    assert len(_read()["cases"]) == 3


def test_public_recorded_trace_is_same_review_and_has_only_allowlisted_metadata():
    evidence = _read()
    trace = json.loads((SHOWCASE / "data/agent_trace.json").read_text(encoding="utf-8"))
    assert trace["schemaVersion"] == 1
    assert trace["kind"] == "recorded_tool_activity"
    assert trace["measurementSource"] == "real_foundry_run"
    assert trace["reviewedCommit"] == evidence["provenance"]["reviewedCommit"]
    assert trace["sourceSha256"] == evidence["provenance"]["sourceSha256"]
    assert trace["toolCallCount"] == evidence["observability"]["toolSpanCount"]
    assert trace["toolCallCount"] == len(trace["events"]) == 16
    assert trace["wallDurationMs"] == evidence["observability"]["wallDurationMs"]
    assert trace["otelTraceId"] is None
    assert trace["tokenUsage"] is None
    assert trace["estimatedCost"] is None
    assert trace["agentDurations"] is None
    assert trace["otelExporterConfigured"] is False
    assert sum(trace["toolCounts"].values()) == 16
    valid = {
        "profile_source", "inspect_approved_policy", "inspect_orders",
        "inspect_reconciliation", "check_quality", "read_project_file",
    }
    for index, event in enumerate(trace["events"], start=1):
        assert event["seq"] == index
        assert event["name"] in valid
        assert event["status"] in {"ok", "error"}
        assert 0 <= event["startSeconds"] <= trace["wallDurationMs"] / 1000
        assert event["durationMs"] >= 0
        assert set(event) == {"seq", "startSeconds", "name", "durationMs", "status"}
    assert "prompt" not in json.dumps(trace).lower()
