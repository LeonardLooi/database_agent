#!/usr/bin/env python3
"""
Fetches and categorizes PR review feedback using the LOGAF scale.

Usage:
    uv run fetch_pr_feedback.py [--pr NUMBER]

Output (JSON):
    {
      "pr": {"number": 123, "branch": "feat/foo"},
      "feedback": {
        "high":     [{"body": "...", "author": "...", "path": "...", "line": N, "thread_id": "...", "review_bot": false}],
        "medium":   [...],
        "low":      [...],
        "bot":      [...],
        "resolved": [...]
      }
    }

LOGAF levels:
  high     - h:, blocker, security, "changes requested" state
  medium   - m:, standard feedback
  low      - l:, nit, style, suggestion
  bot      - informational bots (Codecov, Dependabot summaries) — NOT review bots
  resolved - already resolved threads

Review bot items (sentry, warden, cursor, bugbot, codeql, etc.) appear in
high/medium/low with review_bot=true — they are NOT placed in the bot bucket.
"""

import argparse
import json
import re
import subprocess
import sys
from typing import Any


# Informational bots that post status/coverage summaries — skip entirely
INFORMATIONAL_BOTS = frozenset([
    "codecov",
    "codecov[bot]",
    "dependabot",
    "dependabot[bot]",
    "renovate",
    "renovate[bot]",
    "github-actions",
    "github-actions[bot]",
    "allcontributors",
    "allcontributors[bot]",
    "stale",
    "stale[bot]",
])

# Review bots that post actionable findings — treat as human feedback
REVIEW_BOTS = frozenset([
    "sentry",
    "sentry[bot]",
    "warden",
    "cursor",
    "cursor[bot]",
    "bugbot",
    "bugbot[bot]",
    "seer",
    "codeql",
    "codeql[bot]",
    "codeclimate",
    "codeclimate[bot]",
    "sonarcloud",
    "sonarcloud[bot]",
    "deepsource",
    "deepsource[bot]",
    "snyk",
    "snyk[bot]",
])

# High-priority keyword patterns
HIGH_PATTERNS = re.compile(
    r"^\s*(h:|h\s*:|blocker|BLOCKER|security|security issue|breaking change|must fix|must change)",
    re.IGNORECASE,
)

# Low-priority keyword patterns
LOW_PATTERNS = re.compile(
    r"^\s*(l:|l\s*:|nit:|nit\b|nitpick|style:|style\b|suggestion:|optional:|minor:|\[nit\]|\[optional\])",
    re.IGNORECASE,
)

# Medium-priority keyword patterns
MEDIUM_PATTERNS = re.compile(
    r"^\s*(m:|m\s*:|should|consider|would be better|recommend)",
    re.IGNORECASE,
)


def run_gh(args: list[str]) -> str:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[fetch_pr_feedback] gh error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def run_gh_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    var_args: list[str] = []
    for key, val in variables.items():
        var_args += ["-f", f"{key}={val}"]

    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}", *var_args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[fetch_pr_feedback] GraphQL error: {result.stderr.strip()}", file=sys.stderr)
        return {}
    return json.loads(result.stdout)


def get_current_pr_number() -> int:
    raw = run_gh(["pr", "view", "--json", "number", "-q", ".number"])
    try:
        return int(raw)
    except ValueError:
        print("[fetch_pr_feedback] No PR found for current branch.", file=sys.stderr)
        sys.exit(1)


def get_pr_info(pr_number: int) -> dict[str, Any]:
    raw = run_gh([
        "pr", "view", str(pr_number),
        "--json", "number,headRefName,reviewDecision",
    ])
    return json.loads(raw)


def get_review_threads(owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
    """Fetch all review threads via GraphQL to get thread IDs and resolution state."""
    query = """
    query($owner: String!, $repo: String!, $pr: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $pr) {
          reviewThreads(first: 100) {
            nodes {
              id
              isResolved
              comments(first: 10) {
                nodes {
                  id
                  body
                  author { login }
                  path
                  line
                  createdAt
                }
              }
            }
          }
        }
      }
    }
    """
    data = run_gh_graphql(query, {"owner": owner, "repo": repo, "pr": str(pr_number)})
    try:
        return data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    except (KeyError, TypeError):
        return []


def get_repo_info() -> tuple[str, str]:
    """Return (owner, repo) from gh repo view."""
    raw = run_gh(["repo", "view", "--json", "owner,name"])
    info = json.loads(raw)
    return info["owner"]["login"], info["name"]


def is_informational_bot(login: str) -> bool:
    return login.lower() in INFORMATIONAL_BOTS


def is_review_bot(login: str) -> bool:
    return login.lower() in REVIEW_BOTS


def classify_logaf(body: str, is_changes_requested: bool = False) -> str:
    """Classify a comment body to a LOGAF level."""
    if is_changes_requested:
        return "high"
    if HIGH_PATTERNS.match(body):
        return "high"
    if LOW_PATTERNS.match(body):
        return "low"
    if MEDIUM_PATTERNS.match(body):
        return "medium"
    # Default: medium for standard review comments
    return "medium"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and categorize PR review feedback.")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch PR)")
    args = parser.parse_args()

    pr_number = args.pr or get_current_pr_number()
    pr_info = get_pr_info(pr_number)

    # Changes-requested state elevates all comments from that reviewer to high
    is_changes_requested = pr_info.get("reviewDecision") == "CHANGES_REQUESTED"

    owner, repo = get_repo_info()
    threads = get_review_threads(owner, repo, pr_number)

    feedback: dict[str, list[dict[str, Any]]] = {
        "high": [],
        "medium": [],
        "low": [],
        "bot": [],
        "resolved": [],
    }

    for thread in threads:
        thread_id = thread.get("id", "")
        is_resolved = thread.get("isResolved", False)
        comments = thread.get("comments", {}).get("nodes", [])

        if not comments:
            continue

        # Use the first (root) comment for classification
        root = comments[0]
        author_login = root.get("author", {}).get("login", "unknown")
        body = root.get("body", "").strip()
        path = root.get("path") or ""
        line = root.get("line")

        item: dict[str, Any] = {
            "body": body,
            "author": author_login,
            "path": path,
            "line": line,
            "thread_id": thread_id,
        }

        if is_resolved:
            feedback["resolved"].append(item)
            continue

        if is_informational_bot(author_login):
            feedback["bot"].append(item)
            continue

        review_bot = is_review_bot(author_login)
        item["review_bot"] = review_bot

        level = classify_logaf(body, is_changes_requested)
        feedback[level].append(item)

    output = {
        "pr": {
            "number": pr_info.get("number", pr_number),
            "branch": pr_info.get("headRefName", "unknown"),
        },
        "feedback": feedback,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
