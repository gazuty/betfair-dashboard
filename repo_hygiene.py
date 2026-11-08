"""Refuse betting data, credentials and notebook outputs in this public repository.

The pre-commit hook (nbstripout) is the prevention: it strips notebook outputs
before they are committed. This module is the backstop, run by CI on every push
and pull request:

    python repo_hygiene.py                    # the tracked tree
    python repo_hygiene.py --range BASE..HEAD  # every commit in a push or PR

Checking each commit matters because the repo merges with merge commits: a file
added in one commit and deleted in the next would otherwise pass a check of the
final tree but still land in public history. By the time CI runs, a pushed branch
is already public, so a failure means "remove it before merging", not "it never
left your machine".
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

REPO = Path(__file__).resolve().parent

# Extensions that hold tabular data, archives, databases or keys. Compared
# lower-cased: Windows, Excel and Drive often write ".CSV" or ".XLSX".
FORBIDDEN_EXTENSIONS = {
    # tables and spreadsheets
    "csv", "tsv", "xlsx", "xlsm", "xls", "ods", "numbers",
    # columnar and pickled frames, databases
    "parquet", "feather", "pkl", "pickle", "db", "sqlite", "sqlite3",
    # archives that could carry any of the above
    "zip", "gz", "7z", "tar",
    # credentials
    "json", "p12", "pfx", "pem", "key",
    # rendered notebook exports carry the same results as outputs
    "html", "htm", "pdf",
    # the master's write-then-swap temporary file
    "tmp",
}  # fmt: skip

# Exact paths, or one-level globs where "*" never crosses "/". Compared lower-cased.
ALLOWED = [
    ".env.example",
    ".clasp.json",
    "scripts/appsscript.json",
    "samples/*.csv",
    "tests/fixtures/*.json",
]


def _glob(path: str, pattern: str) -> bool:
    """Match ``path`` against ``pattern`` where ``*`` stays within one path segment."""
    regex = "".join("[^/]*" if ch == "*" else re.escape(ch) for ch in pattern)
    return re.fullmatch(regex, path) is not None


def forbidden_reason(path: str) -> str | None:
    """Return why ``path`` may not be committed, or None if it may."""
    lowered = path.lower()
    if any(_glob(lowered, p) for p in ALLOWED):
        return None
    parts = lowered.split("/")
    name = parts[-1]
    if ".secrets" in parts[:-1]:
        return "inside a .secrets/ folder"
    # Any ".env" prefix (.env.local, .env-prod, direnv's .envrc); .env.example is in ALLOWED.
    if name.startswith(".env") or name.endswith(".env"):
        return "an environment file"
    if "." in name and name.rsplit(".", 1)[1] in FORBIDDEN_EXTENSIONS:
        return f"a .{name.rsplit('.', 1)[1]} file (data, archive or key)"
    return None


def notebook_problems(text: str, label: str) -> list[str]:
    """Return what a notebook's JSON carries that must not be committed."""
    try:
        nb = json.loads(text)
    except json.JSONDecodeError as error:
        return [f"{label}: not valid notebook JSON ({error.msg})"]
    problems = []
    if "colab" in nb.get("metadata", {}):
        problems.append(f"{label}: Colab metadata")
    for i, cell in enumerate(nb.get("cells", [])):
        if cell.get("outputs") or cell.get("execution_count") is not None:
            problems.append(f"{label} cell {i}: outputs")
        if cell.get("attachments"):
            # Pasted images (a screenshot of a P/L table) live here as base64.
            problems.append(f"{label} cell {i}: attachments")
        if {"colab", "outputId"} & set(cell.get("metadata", {})):
            problems.append(f"{label} cell {i}: Colab metadata")
    return problems


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout


def tracked_tree_problems() -> list[str]:
    """Check every tracked file as it is in the working tree."""
    problems = []
    for path in filter(None, _git("ls-files", "-z").split("\0")):
        if reason := forbidden_reason(path):
            problems.append(f"{path}: {reason}")
        elif path.lower().endswith(".ipynb"):
            text = (REPO / path).read_text(encoding="utf-8")
            problems.extend(notebook_problems(text, path))
    return problems


def _commits(spec: str) -> list[str]:
    start, _, end = spec.partition("..")
    if not start or not end:
        # An empty side would make rev-list check nothing and report success.
        raise ValueError(f"expected BASE..HEAD with both commits, got {spec!r}")
    if re.fullmatch(r"0+", start):
        # GitHub sends an all-zero "before" when the branch is created. Check only
        # the pushed commit; walking all history would re-report data already there.
        return [_git("rev-parse", end).strip()]
    return _git("rev-list", f"{start}..{end}").split()


def range_problems(spec: str) -> list[str]:
    """Check every file each commit in ``spec`` adds or modifies."""
    problems = []
    for commit in _commits(spec):
        short = commit[:7]
        # For a merge, -c lists only paths that differ from every parent: what the
        # merge itself introduced (e.g. a file staged while resolving conflicts).
        is_merge = len(_git("rev-list", "--parents", "-n", "1", commit).split()) > 2
        changed = _git(
            "diff-tree", "-r", "--root", "--no-commit-id", "--name-only", "-z",
            *(["-c"] if is_merge else ["--diff-filter=AMR"]), commit,
        )  # fmt: skip
        for path in filter(None, changed.split("\0")):
            if reason := forbidden_reason(path):
                problems.append(f"{short} adds {path}: {reason}")
            elif path.lower().endswith(".ipynb"):
                text = _git("show", f"{commit}:{path}")
                problems.extend(notebook_problems(text, f"{short} {path}"))
    return problems


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--range", help="check each commit in BASE..HEAD")
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        problems = range_problems(args.range) if args.range else tracked_tree_problems()
    except subprocess.CalledProcessError as error:
        # e.g. a force-push to main: the old "before" commit is not in the clone.
        print(f"❌ git could not read the commits to check: {error.stderr.strip()}")
        print("   The guard cannot vouch for this push; check the new commits by hand.")
        return 1
    for problem in problems:
        print(f"❌ {problem}")
    if problems:
        print("Remove these before merging (see README, Development).")
        return 1
    print("✅ no data, credentials or notebook outputs found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
