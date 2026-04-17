#!/usr/bin/env python3
"""
Fetches CI check status for a PR and extracts failure log snippets.

Usage:
    uv run fetch_pr_checks.py [--pr NUMBER]

Output (JSON):
    {
      "pr": {"number": 123, "branch": "feat/foo"},
      "summary": {"total": 5, "passed": 3, "failed": 2, "pending": 0},
      "checks": [
        {"name": "tests", "status": "fail", "log_snippet": "...", "run_id": 123},
        {"name": "lint", "status": "pass"}
      ]
    }

Statuses: "pass" | "fail" | "pending"
"""

import argparse
import json
import subprocess
import sys
from typing import Any


LOG_SNIPPET_LINES = 50  # lines to capture from failed run logs


def run_gh(args: list[str]) -> str:
    result = subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[fetch_pr_checks] gh error: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout.strip()


def get_current_pr_number() -> int:
    raw = run_gh(["pr", "view", "--json", "number", "-q", ".number"])
    try:
        return int(raw)
    except ValueError:
        print("[fetch_pr_checks] No PR found for current branch.", file=sys.stderr)
        sys.exit(1)


def get_pr_info(pr_number: int) -> dict[str, Any]:
    raw = run_gh([
        "pr", "view", str(pr_number),
        "--json", "number,headRefName",
    ])
    return json.loads(raw)


def get_checks(pr_number: int) -> list[dict[str, Any]]:
    raw = run_gh([
        "pr", "checks", str(pr_number),
        "--json", "name,state,link",
    ])
    return json.loads(raw)


def normalize_state(state: str) -> str:
    """Normalize gh check states to pass/fail/pending."""
    state = state.lower()
    if state in ("success", "pass", "completed"):
        return "pass"
    if state in ("failure", "fail", "error", "timed_out", "action_required"):
        return "fail"
    return "pending"


def extract_run_id(link: str) -> str | None:
    """Extract GitHub Actions run ID from a check link URL."""
    if not link:
        return None
    # URL pattern: /actions/runs/<run_id>
    parts = link.split("/")
    try:
        idx = parts.index("runs")
        return parts[idx + 1].split("?")[0]
    except (ValueError, IndexError):
        return None


def get_log_snippet(run_id: str) -> str:
    """Fetch the last N lines of failed job logs for a run."""
    result = subprocess.run(
        ["gh", "run", "view", run_id, "--log-failed"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return result.stderr.strip() or "(no log output available)"

    lines = result.stdout.strip().splitlines()
    snippet = lines[-LOG_SNIPPET_LINES:] if len(lines) > LOG_SNIPPET_LINES else lines
    return "\n".join(snippet)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch PR CI check status and log snippets.")
    parser.add_argument("--pr", type=int, help="PR number (default: current branch PR)")
    args = parser.parse_args()

    pr_number = args.pr or get_current_pr_number()
    pr_info = get_pr_info(pr_number)

    raw_checks = get_checks(pr_number)

    checks: list[dict[str, Any]] = []
    summary = {"total": 0, "passed": 0, "failed": 0, "pending": 0}

    for check in raw_checks:
        name = check.get("name", "unknown")
        state = normalize_state(check.get("state", ""))
        link = check.get("link", "")

        entry: dict[str, Any] = {"name": name, "status": state}

        if state == "fail":
            run_id = extract_run_id(link)
            if run_id:
                entry["run_id"] = run_id
                entry["log_snippet"] = get_log_snippet(run_id)
            else:
                entry["log_snippet"] = "(could not extract run ID from link)"

        checks.append(entry)
        summary["total"] += 1
        if state == "pass":
            summary["passed"] += 1
        elif state == "fail":
            summary["failed"] += 1
        else:
            summary["pending"] += 1

    output = {
        "pr": {
            "number": pr_info.get("number", pr_number),
            "branch": pr_info.get("headRefName", "unknown"),
        },
        "summary": summary,
        "checks": checks,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
