"""Review must be bound to the exact source, implementation, contract and output."""
import pytest

from agentic.verify import collect_provenance, verify_manifest


def fake_manifest():
    return {
        "provenance": collect_provenance(),
        "agent_reviews": [
            {"role": name, "summary": "A structured audit of this pipeline.", "findings": [],
             "recommended_next_action": "Review deterministic quality evidence."}
            for name in ("data_architect", "data_engineer", "verification_engineer")
        ],
    }


def test_report_is_cryptographically_bound_to_checked_in_files():
    assert verify_manifest(fake_manifest())["provenance_matched"]


def test_stale_policy_is_not_attested():
    manifest = fake_manifest()
    manifest["provenance"]["policy_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="stale"):
        verify_manifest(manifest)


def test_missing_agent_is_not_attested():
    manifest = fake_manifest()
    manifest["agent_reviews"].pop()
    with pytest.raises(ValueError, match="order"):
        verify_manifest(manifest)
