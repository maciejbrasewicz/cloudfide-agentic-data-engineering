"""Official GitHub MCP Server, hard-limited to read-only repository review.

The GitHub Actions job token has contents:read + pull-requests:read only.
No personal access token, repository secret or write permission is needed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

IMAGE = "ghcr.io/github/github-mcp-server:v2.1.0"
_TOOLSETS = "repos,pull_requests"


@dataclass(frozen=True)
class GithubMCPConfig:
    name: str
    command: str
    args: tuple[str, ...]


def config_from_environment() -> GithubMCPConfig | None:
    if os.getenv("GITHUB_MCP_READONLY") != "1":
        return None
    if not os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN"):
        raise RuntimeError("GitHub MCP requested but Actions read-only token is missing")
    return GithubMCPConfig(
        name="github_readonly",
        command="docker",
        args=(
            "run", "-i", "--rm",
            "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
            "-e", "GITHUB_TOOLSETS=" + _TOOLSETS,
            "-e", "GITHUB_READ_ONLY=true",
            IMAGE,
        ),
    )
