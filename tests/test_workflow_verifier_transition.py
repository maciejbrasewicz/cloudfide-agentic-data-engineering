"""Regression for actual portal run 44501856719: P5 says WAITING_VERIFIER,
but GitHub silently skipped Verifier after non-selected rework branch was skipped.

GitHub's implicit success() evaluation can propagate skipped ancestors; only an
explicit always() + verified P5 output may resume the independent Verifier.
"""
from pipeline import ROOT


def _job(text: str, name: str, next_name: str) -> str:
    start = "  " + name + ":\n"
    end = "  " + next_name + ":\n"
    assert start in text and end in text
    return text.split(start, 1)[1].split(end, 1)[0]


def test_p5_requires_real_state_before_verifier_not_skipped_ancestor_success():
    workflow = (ROOT / ".github/workflows/engineer-e2e.yml").read_text(encoding="utf-8")
    verifier = _job(workflow, "verifier", "adversarial")
    assert "needs: [p5-state]" in verifier
    assert "always()" in verifier
    assert "needs['p5-state'].result == 'success'" in verifier
    assert "needs['p5-state'].outputs.selected_status == 'WAITING_VERIFIER'" in verifier
    assert "Azure OIDC" in verifier


def test_independent_p4_verifier_must_run_after_successful_p5_despite_skipped_retry():
    workflow = (ROOT / ".github/workflows/engineer-e2e.yml").read_text(encoding="utf-8")
    p4 = _job(workflow, "adversarial", "publish-draft-pr")
    assert "needs: verifier" in p4
    assert "if: ${{ always() && needs.verifier.result == 'success' }}" in p4
    assert "Execute ONLY Verifier test against known-broken candidate (must FAIL)" in p4


def test_pub_requires_successful_adversarial_gate_and_never_auto_merges():
    workflow = (ROOT / ".github/workflows/engineer-e2e.yml").read_text(encoding="utf-8")
    publisher = _job(workflow, "publish-draft-pr", "policy-review")
    assert "always()" in publisher
    assert "needs.adversarial.result == 'success'" in publisher
    assert "gh pr create" in publisher and "--draft" in publisher
    assert "gh pr merge" not in publisher
