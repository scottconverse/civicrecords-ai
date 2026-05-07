#!/usr/bin/env python3
"""Fail the release gate when tracked source contains committed secrets."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ALLOWLIST = {
    ".env.example",
    "README.md",
    "README.txt",
    "USER-MANUAL.md",
    "USER-MANUAL.txt",
    "CHANGELOG.md",
    "docs/UNIFIED-SPEC.md",
    "docs/index.html",
}

SECRET_PATTERNS = [
    (
        "real JWT secret assignment",
        re.compile(r"(?i)\bJWT_SECRET\s*=\s*(?!CHANGE-ME|<|example|your-|\$)[A-Za-z0-9_./+=:-]{24,}"),
    ),
    (
        "real first-admin password assignment",
        re.compile(
            r"(?i)\bFIRST_ADMIN_PASSWORD\s*=\s*(?!CHANGE-ME|<|example|your-|\$)[^\s#]{12,}"
        ),
    ),
    (
        "real encryption key assignment",
        re.compile(
            r"(?i)\bENCRYPTION_KEY\s*=\s*(?!CHANGE-ME|<|example|your-|\$)[A-Za-z0-9_-]{40,}={0,2}"
        ),
    ),
    (
        "private key block",
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
]


def tracked_files() -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=ROOT, text=False
    )
    return [p.decode("utf-8") for p in output.split(b"\0") if p]


def is_text_file(path: Path) -> bool:
    try:
        chunk = path.read_bytes()[:4096]
    except OSError:
        return False
    return b"\0" not in chunk


def main() -> int:
    findings: list[str] = []
    tracked = tracked_files()

    if ".env" in tracked:
        findings.append(".env is tracked; runtime environment files must remain local only")

    for rel in tracked:
        path = ROOT / rel
        if (
            rel in ALLOWLIST
            or rel.startswith(".github/workflows/")
            or rel.startswith("backend/tests/")
            or not path.is_file()
            or not is_text_file(path)
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                findings.append(f"{rel}: matched {label}")

    if findings:
        print("SECRET-SCAN: FAILED")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print(f"SECRET-SCAN: PASSED ({len(tracked)} tracked file(s) scanned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
