#!/usr/bin/env python3
"""Git state detection for handoff-skill.

Usage:
    python3 git.py [project_root]

Output: JSON with recent commits, changed files, and date range.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_git(args: list, cwd: Path) -> str:
    """Run a git command and return stdout, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd), capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def detect_git(root: Path) -> dict:
    """Gather git state information."""
    info = {
        "has_git": False,
        "branch": "",
        "recent_commits": [],
        "changed_files": [],
        "dirty": False,
        "date_range": "",
        "error": None,
    }

    # Check if git repo exists
    rev_parse = run_git(["rev-parse", "--git-dir"], root)
    if not rev_parse:
        info["error"] = "Not a git repository"
        return info

    info["has_git"] = True

    # Branch
    info["branch"] = run_git(["branch", "--show-current"], root)

    # Recent commits
    log = run_git(["log", "--oneline", "-10"], root)
    if log:
        info["recent_commits"] = log.splitlines()

    # Changed files (last 5 commits or all changes)
    diff_files = run_git(["diff", "--name-only", "HEAD~5..HEAD"], root)
    if not diff_files:
        diff_files = run_git(["diff", "--name-only", "HEAD"], root)
    if diff_files:
        info["changed_files"] = [f for f in diff_files.splitlines() if f.strip()]

    # Dirty working tree
    status = run_git(["status", "--porcelain"], root)
    if status:
        info["dirty"] = True

    # Date range — last 5 commits (or fewer if history is short)
    # HEAD~5 date if available, otherwise first commit date
    head_date = run_git(["log", "--format=%as", "-1"], root)
    older_date = run_git(["log", "--format=%as", "-1", "HEAD~5"], root)
    if not older_date:
        # Fewer than 5 commits — use the first commit
        older_date = run_git(["log", "--reverse", "--format=%as", "-1"], root)
    if head_date and older_date and head_date != older_date:
        info["date_range"] = f"{older_date} ~ {head_date}"
    elif head_date:
        info["date_range"] = head_date
    else:
        info["date_range"] = datetime.now().strftime("%Y-%m-%d")

    return info


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    result = detect_git(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
