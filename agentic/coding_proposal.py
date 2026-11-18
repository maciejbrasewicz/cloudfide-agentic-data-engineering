"""Autonomous Foundry code author: limited *new regression test* proposal.

The author writes actual Python, but receives no repository write permissions.
A separate no-secret validation job runs generated tests in an ephemeral runner;
a final GitHub job opens a DRAFT PR. The human is the only merge authority.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pipeline import ROOT
from .tools import read_project_file, check_quality


OUTPUT_FILE = "tests/test_agent_generated_regression.py"
MAX_CONTENT = 7_000


class CodeProposal(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["new_regression_test"] = "new_regression_test"
    file_path: Literal["tests/test_agent_generated_regression.py"] = OUTPUT_FILE
    code: str = Field(min_length=100, max_length=MAX_CONTENT)
    rationale: str = Field(min_length=30, max_length=800)
    test_claim: str = Field(min_length=20, max_length=500)


def parse_proposal(payload: str) -> CodeProposal:
    text = payload.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return CodeProposal.model_validate_json(text)


def validate_content(proposal: CodeProposal, root: Path = ROOT) -> Path:
    """Reject writes to any existing file; never execute model-provided commands."""
    import ast
    target = root / OUTPUT_FILE
    if target.exists() or target.is_symlink():
        raise ValueError("Refuse to overwrite existing project files")
    source = proposal.code
    if "\x00" in source or "\r" in source:
        raise ValueError("Invalid Python source encoding")
    parsed = ast.parse(source, filename=OUTPUT_FILE)
    if not any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and
               node.name.startswith("test_") for node in parsed.body):
        raise ValueError("Proposed code must include a test function")
    if source.count("\n") > 240:
        raise ValueError("Generated test exceeds bounded line count")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source if source.endswith("\n") else source + "\n", encoding="utf-8")
    return target


async def author() -> CodeProposal:
    from agent_framework import Agent
    from agent_framework.foundry import FoundryChatClient
    from azure.identity import DefaultAzureCredential

    endpoint=os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    model=os.getenv("FOUNDRY_MODEL")
    if not endpoint or not model:
        raise RuntimeError("Foundry project endpoint and deployment are required")
    credential=DefaultAzureCredential(exclude_interactive_browser_credential=True)
    client=FoundryChatClient(project_endpoint=endpoint, model=model, credential=credential)
    agent=Agent(
        name="regression_code_author",
        client=client,
        instructions="""You are a focused Python quality engineer authorized to PROPOSE ONE NEW REGRESSION TEST FILE.
Read solution.py, pipeline.py, tests/test_solution.py and tests/test_raw_oracle.py. Call check_quality.
Output exactly one JSON object with keys: kind='new_regression_test',
file_path='tests/test_agent_generated_regression.py', code, rationale and test_claim.
Write real executable Python pytest code, no fabricated claims. Focus on an untested
edge case in the supplied task, ideally virtual-column expression rejection or immutable
input behavior. Do not edit or overwrite anything. The code will run in an isolated
CI sandbox with no cloud credentials and then be proposed to a human as a draft PR.
No shell commands, network, file I/O, dynamic code loading, environment access,
eval or exec. Use only pytest, pandas and already included project modules.""",
        tools=[read_project_file,check_quality],
    )
    response=await agent.run(
        "Generate exactly one useful additional regression test for the current CloudFide task. "
        "Return JSON with complete Python test source and an evidence-based justification."
    )
    return parse_proposal(response.text)


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--generate",action="store_true")
    parser.add_argument("--validate-only",type=Path)
    parser.add_argument("--root",type=Path,default=ROOT)
    parser.add_argument("--output",type=Path,default=ROOT / "agent_code_proposal.json")
    args=parser.parse_args()
    if bool(args.generate)==bool(args.validate_only):
        parser.error("Choose exactly one of --generate or --validate-only")
    if args.generate:
        proposal=asyncio.run(author())
        args.output.write_text(proposal.model_dump_json(indent=2)+"\n",encoding="utf-8")
        print("Foundry proposed a bounded regression test; human review required")
    else:
        proposal=CodeProposal.model_validate_json(args.validate_only.read_text(encoding="utf-8"))
        file=validate_content(proposal,args.root)
        print("Validated restricted new test file",file)


if __name__=="__main__":
    main()
