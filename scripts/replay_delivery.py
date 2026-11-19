"""Reproduce one independently published candidate safely, without running its code on host.

Usage:
  uv run --no-sync python scripts/replay_delivery.py \
     --run-id 44485096373 \
     --commit 73ab197159f8ed5a595bdd99a88b01707371d12e \
     --base 737baf62ad7fb17f89a194a4dcb904bf0081ceea

Requires Docker. Uses the same trusted admission, static sandbox and
independent CSV/Decimal oracle as the exact-SHA GitHub CI.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agentic.candidate_branch_ci import stage_exact_branch  # noqa: E402

SHA = re.compile(r"[a-f0-9]{40}\Z")
RUN_ID = re.compile(r"[0-9]{5,30}\Z")


def execute(command: list[str], *, cwd: Path, timeout: int) -> None:
    subprocess.run(command, cwd=cwd, check=True, timeout=timeout)


def prepare_branch(run_id: str, expected_sha: str, base_sha: str, destination: Path) -> dict:
    if not RUN_ID.fullmatch(run_id) or not SHA.fullmatch(expected_sha) or not SHA.fullmatch(base_sha):
        raise ValueError("Only exact run ID, Git SHA-40 and base SHA-40 are accepted")
    branch = "agentic-delivery/run-" + run_id
    execute(
        ["git", "fetch", "--no-tags", "origin",
         "refs/heads/" + branch + ":refs/remotes/origin/" + branch],
        cwd=ROOT, timeout=40,
    )
    return stage_exact_branch(
        root=ROOT, destination=destination, branch=branch,
        commit_sha=expected_sha, base_sha=base_sha, source_run_id=run_id,
    )


def verify_candidate(directory: Path, receipt_dir: Path) -> dict:
    """Only Docker may import candidate code; host imports trusted oracle only."""
    if not shutil.which("docker"):
        raise RuntimeError("Docker is required to execute untrusted candidate code safely")
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.chmod(0o777)
    image_name = "cloudfide-trusted-replay:verified"
    execute(["docker", "build", "-f", "sandbox/Dockerfile", "-t", image_name, "sandbox"],
            cwd=ROOT, timeout=240)
    execute([
        "docker", "run", "--rm",
        "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--pids-limit", "128", "--memory", "768m", "--cpus", "1.5",
        "--user", "65534:65534",
        "--tmpfs", "/tmp:rw,nosuid,nodev,mode=1777,size=128m",
        "--volume", str(directory.resolve()) + ":/input:ro",
        "--volume", str(receipt_dir.resolve()) + ":/out:rw",
        image_name,
    ], cwd=ROOT, timeout=300)
    from agentic.p3_oracle import validate_runner

    verdict = validate_runner(ROOT / "sales.csv", receipt_dir)
    (receipt_dir / "verification.json").write_text(
        json.dumps(verdict, indent=2) + "\n", encoding="utf-8"
    )
    if verdict["status"] != "PASSED" or verdict.get("reconciliation") != "passed":
        raise RuntimeError("Independent candidate validation failed; see verification.json")
    return verdict


def main() -> None:
    p = argparse.ArgumentParser(description="Replay exact-SHA agent candidate in a secret-free Docker sandbox")
    p.add_argument("--run-id", required=True)
    p.add_argument("--commit", required=True, help="Exact candidate commit SHA from draft PR")
    p.add_argument("--base", required=True, help="Original source commit SHA from delivery manifest")
    p.add_argument("--evidence-dir", type=Path,
                   help="Optional directory to preserve test, pipeline and oracle logs")
    args = p.parse_args()
    with tempfile.TemporaryDirectory(prefix="cloudfide-replay-") as temp:
        tmp = Path(temp)
        input_dir = tmp / "admitted-input"
        temp_output = tmp / "sandbox-output"
        admission = prepare_branch(args.run_id, args.commit, args.base, input_dir)
        print("SHA-verified candidate admitted:", json.dumps({
            "run": args.run_id, "commit": args.commit,
            "files": admission["file_count"]
        }))
        result = verify_candidate(input_dir, temp_output)
        if args.evidence_dir:
            target = args.evidence_dir.resolve()
            target.mkdir(parents=True, exist_ok=True)
            for name in ("tests.log", "pipeline.log", "verification.json", "revenue_by_region.csv"):
                shutil.copyfile(temp_output / name, target / name)
        print(json.dumps({
            "status": result["status"], "reconciliation": result["reconciliation"],
            "net_revenue": result["net_revenue"], "regions": result["regions"],
            "candidate_sha": args.commit, "source_run_id": args.run_id,
            "execution": "isolated_docker_not_host_python"
        }, indent=2))


if __name__ == "__main__":
    main()
