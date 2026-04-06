#!/usr/bin/env python3
"""
sync_docs_check.py — Post-commit doc-sync reminder.

Reads `git diff HEAD~1 --stat`, maps changed files to docs that likely
need updating, and prints an actionable report.

Usage:
    python scripts/sync_docs_check.py          # check last commit
    python scripts/sync_docs_check.py --staged # check staged changes (pre-commit)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ── Sync table: file prefix → docs to update ─────────────────────────────────
# Keys are path prefixes (checked with str.startswith).
# Values are human-readable doc references.

SYNC_TABLE: dict[str, list[str]] = {
    "dashboard/tabs/":      ["COMO_RODAR.md (tab descriptions)", "docs/AGENTS.md (Estado Atual)"],
    "dashboard/app.py":     ["COMO_RODAR.md (tab names/order)"],
    "dashboard/kpis.py":    ["docs/CONTEXT.md (KPI section if indicators changed)"],
    "dashboard/charts.py":  ["docs/AGENTS.md (recent sessions — new chart types)"],
    "dashboard/constants.py": ["docs/AGENTS.md (ticker count)", "CLAUDE.md (TICKER_MAP note)"],
    "dashboard/loaders.py": ["docs/CONTEXT.md (Data Flow section)"],
    "src/scraper.py":       ["docs/CONTEXT.md (Pipeline section)", "CLAUDE.md (Scraper Core)"],
    "src/database.py":      ["docs/CONTEXT.md (Database section)", "CLAUDE.md (Database)"],
    "src/standardizer.py":  ["docs/CONTEXT.md (account normalization rules)"],
    "scripts/":             ["README.md (workflow)", "CLAUDE.md (Scripts Structure)"],
    "tests/":               ["docs/AGENTS.md (test count in Estado Atual)"],
    "requirements.txt":     ["docs/CONTEXT.md (Stack section)"],
    "cvm_pyqt_app.py":      ["docs/AGENTS.md (App Desktop section)", "README.md"],
    "docs/":                [],  # doc changes don't trigger other doc updates
}


def get_changed_files(staged: bool = False) -> list[str]:
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only"]
    else:
        cmd = ["git", "diff", "HEAD~1", "--name-only"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except subprocess.CalledProcessError:
        # Fallback: compare against empty tree (first commit or no prior commit)
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True, text=True, check=True
            )
            return [f.strip() for f in result.stdout.splitlines() if f.strip()]
        except subprocess.CalledProcessError:
            return []


def map_to_docs(changed_files: list[str]) -> dict[str, list[str]]:
    """Return {changed_file: [docs to update]}."""
    result: dict[str, list[str]] = {}
    for f in changed_files:
        matched = []
        for prefix, docs in SYNC_TABLE.items():
            if f.startswith(prefix) and docs:
                matched.extend(docs)
        if matched:
            result[f] = list(dict.fromkeys(matched))  # deduplicate, preserve order
    return result


def main() -> None:
    staged = "--staged" in sys.argv
    changed = get_changed_files(staged)

    if not changed:
        print("[sync-docs] No changed files detected.")
        return

    mapping = map_to_docs(changed)

    if not mapping:
        print("[sync-docs] No doc updates needed for this commit.")
        return

    # Aggregate: docs → files that triggered them
    docs_needed: dict[str, list[str]] = {}
    for f, docs in mapping.items():
        for doc in docs:
            docs_needed.setdefault(doc, []).append(f)

    print()
    print("=" * 60)
    print("  sync-docs: docs to review after this commit")
    print("=" * 60)
    for doc, triggers in sorted(docs_needed.items()):
        trigger_str = ", ".join(Path(t).name for t in triggers[:3])
        if len(triggers) > 3:
            trigger_str += f" +{len(triggers) - 3} more"
        print(f"  • {doc}")
        print(f"    triggered by: {trigger_str}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
