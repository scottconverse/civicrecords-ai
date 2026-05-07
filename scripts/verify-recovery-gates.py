#!/usr/bin/env python3
"""Release-truth gates added after the 2026-05-07 external audit."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = [
    "docs/release-recovery-status.md",
    "docs/audits/civicrecords-ai-audit-full-2026-05-07.md",
    "frontend/playwright.config.ts",
    "frontend/e2e/civicrecords-user-flows.spec.ts",
    "scripts/verify-secret-scan.py",
    "scripts/verify-runtime-install.py",
]

OVERCLAIM_PATTERNS = [
    re.compile(r"\bproduct-ready\b", re.IGNORECASE),
    re.compile(r"\bproduction-ready\b", re.IGNORECASE),
    re.compile(r"\bsubstantially complete\b", re.IGNORECASE),
    re.compile(r"\bwell beyond a simple MVP\b", re.IGNORECASE),
]

CLAIM_SURFACES = [
    "README.md",
    "README.txt",
    "USER-MANUAL.md",
    "USER-MANUAL.txt",
    "docs/index.html",
    "docs/UNIFIED-SPEC.md",
]


def fail(message: str, failures: list[str]) -> None:
    failures.append(message)


def tracked_files() -> set[str]:
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT, text=False)
    return {p.decode("utf-8") for p in output.split(b"\0") if p}


def read_text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []
    tracked = tracked_files()

    for rel in REQUIRED_FILES:
        if not (ROOT / rel).is_file():
            fail(f"missing required recovery artifact: {rel}", failures)

    for rel in CLAIM_SURFACES:
        path = ROOT / rel
        if not path.is_file():
            fail(f"missing claim surface: {rel}", failures)
            continue
        text = read_text(rel)
        if "provisional" not in text.lower() and "do-not-promote" not in text.lower():
            fail(f"{rel}: missing provisional/do-not-promote release labeling", failures)
        for pattern in OVERCLAIM_PATTERNS:
            if pattern.search(text):
                fail(f"{rel}: blocked public overclaim pattern {pattern.pattern}", failures)

    package_json = read_text("frontend/package.json")
    if '"test:e2e"' not in package_json:
        fail("frontend/package.json: missing test:e2e script", failures)
    if '"node": ">=20"' not in package_json:
        fail("frontend/package.json: missing explicit Node >=20 engine", failures)

    verify_release = read_text("scripts/verify-release.sh")
    for token in [
        "verify-recovery-gates.py",
        "verify-secret-scan.py",
        "npm audit --audit-level=moderate",
        "npm run test:e2e",
        "verify-runtime-install.py",
    ]:
        if token not in verify_release:
            fail(f"scripts/verify-release.sh: missing gate command containing {token}", failures)

    if ".env" in tracked:
        fail(".env is tracked; remove runtime secrets from git", failures)

    if failures:
        print("RECOVERY-GATES: FAILED")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("RECOVERY-GATES: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
