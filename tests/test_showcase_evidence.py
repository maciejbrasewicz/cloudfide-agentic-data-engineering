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


def test_showcase_is_bilingual_and_explains_the_real_delivery():
    html = (SHOWCASE / "index.html").read_text(encoding="utf-8")
    for page in ("overview", "task", "architecture", "execution", "data", "cases", "technical", "status", "evidence"):
        assert f'data-section="{page}"' in html
    assert '<script src="./app.js" defer>' in html
    assert '<script src="./technical.js" defer>' in html
    assert '<script src="./delivery_status.js" defer>' in html
    assert '<script src="./reviewer_console.js" defer>' in html
    assert 'id="reviewer-workspace"' in html
    assert 'id="reviewer-recalculate"' in html
    assert 'id="full-agent-console"' in html
    assert 'https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/pull/28' in html
    assert 'https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/actions/runs/44478568225' in html
    assert 'id="delivery-evidence"' in html
    assert 'engineer-e2e.yml' in html
    assert '<link rel="stylesheet" href="./technical.css">' in html
    assert 'id="technical-start-form"' in html
    assert 'id="technical-modules"' in html
    assert "ChatGPT" not in html
    assert "engineering.html" not in html
    assert '<script src="./trace.js" defer>' not in html
    assert 'id="en" data-lang="en"' in html
    assert 'id="pl" data-lang="pl"' in html
    assert "SequentialBuilder" in html
    assert "Microsoft Foundry" in html
    assert "revenue_by_region.csv" in html
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



def test_public_original_foundry_report_excerpts_are_from_same_attested_run():
    evidence = _read()
    trace = json.loads((SHOWCASE / "data/agent_trace.json").read_text(encoding="utf-8"))
    reports = json.loads((SHOWCASE / "data/foundry_reports.json").read_text(encoding="utf-8"))
    assert reports["schemaVersion"] == 1
    assert reports["source"] == "recorded_foundry_report"
    assert reports["runId"] == trace["githubRunId"]
    assert reports["reviewedCommit"] == evidence["provenance"]["reviewedCommit"]
    assert reports["runUrl"] == evidence["provenance"]["reviewUrl"]
    assert [r["role"] for r in reports["roles"]] == [
        "data_architect", "data_engineer", "verification_engineer"
    ]
    assert len(reports["roles"]) == 3
    for role in reports["roles"]:
        assert role["findingCount"] == 11
        assert len(role["selectedFindings"]) == 3
        assert len(role["originalSummary"]) > 300
    assert "unverified" in reports["roles"][1]["originalSummary"]
    assert "79 tests" in reports["roles"][2]["originalSummary"]
    assert "Verbatim English agent summaries" in reports["disclosure"]
    assert reports["originalManifestSha256"] == "d66c9c275581d56bbef286fa80d9d85858087899276918426a8e037516955ba5"
    assert all(len(r["originalRecommendedNextAction"]) > 100 for r in reports["roles"])


def test_polish_and_english_have_complete_static_translation_coverage():
    import re

    html = (SHOWCASE / "index.html").read_text(encoding="utf-8")
    js = (SHOWCASE / "app.js").read_text(encoding="utf-8")
    translation_keys = set(re.findall(r'data-i18n="([a-zA-Z]+)"', html))
    dictionary_source = js.split("const meta = {}", 1)[0]
    for key in translation_keys:
        assert re.search(rf"\b{re.escape(key)}\s*:", dictionary_source), key
    assert len(translation_keys) >= 100
    assert "document.documentElement.lang=language" in js
    assert "renderDynamic()" in js


def test_system_is_one_portal_and_has_no_legacy_personal_branding():
    html = (SHOWCASE / "index.html").read_text(encoding="utf-8")
    js = (SHOWCASE / "app.js").read_text(encoding="utf-8")
    technical = (SHOWCASE / "technical.js").read_text(encoding="utf-8")
    server = (SHOWCASE / "server.mjs").read_text(encoding="utf-8")
    for forbidden in ("ChatGPT", "Human-in-the-loop /", "Engineering Lab"):
        assert forbidden not in html, forbidden
        assert forbidden not in js, forbidden
    assert "engineering.js" not in server
    assert "engineering.css" not in server
    assert "human-in-the-loop" not in technical.lower()
    assert "cloudfide:language" in technical
    assert "data/agent_trace.json" not in technical
    assert "api/live/start" in technical
    assert 'location==="/engineering.html"' in server


def test_real_agent_public_console_is_grounded_in_executed_artifacts():
    record = json.loads((SHOWCASE / "data/autonomous_run.json").read_text(encoding="utf-8"))
    assert record["schemaVersion"] == 1
    assert record["runId"] == 44433630928
    assert record["historical"] is True
    assert record["sourceWorkflowConclusion"] == "failure_at_initial_automated_pull_request_creation"
    assert record["reference"]["candidateSha"] == "287b9d82237e90b753991cd43f3ebd5a2e514a53"
    assert record["result"]["testPassed"] == 18
    assert record["result"]["testCount"] == 18
    assert Decimal(record["result"]["netRevenue"]) == Decimal("2570247.03")
    assert [stage["key"] for stage in record["stages"]] == [
        "architect", "engineer-1", "engineer-2", "engineer-3", "verifier", "delivery",
    ]
    assert [stage["status"] for stage in record["stages"]] == [
        "PASSED", "FAILED", "FAILED", "PASSED", "PASSED", "PASSED",
    ]
    assert len(record["stages"][0]["tools"]) == 7
    assert len(record["stages"][4]["tools"]) == 8
    assert record["stages"][4]["files"][0]["name"] == "tests/test_verifier_generated.py"
    for stage in record["stages"]:
        assert stage["classification"] != "simulated"
        assert stage["sourceUrl"].startswith(
            "https://github.com/maciejbrasewicz/cloudfide-agentic-data-engineering/"
        )
        for file in stage.get("files", []):
            assert len(file["sha256"]) == 64
    assert "original" not in record.keys()
    assert "secret" not in json.dumps(record).lower()
