"""Throwaway file for the live-fire test of the ruff CI gate added in PR #34.

This file deliberately contains a single ruff violation (F401: unused import)
to confirm the new `ruff (lint)` CI job fails CI when violations are present.

DO NOT MERGE. After CI confirms the ruff job fails as expected, the parent
PR is closed without merge and this file goes away with the deleted branch.

Sprint log entry will record the outcome.
"""
import os  # noqa: ruff-test-violation-do-not-fix-this-is-the-point
