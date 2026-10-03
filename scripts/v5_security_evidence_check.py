#!/usr/bin/env python3
"""Validate that the repository contains the Day 32 security-evidence contract."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(results, name, condition, detail):
    results.append((name, bool(condition), detail))


def main() -> int:
    results = []
    workflow = (ROOT / ".github/workflows/v5-security-evidence.yml").read_text(encoding="utf-8")
    review = (ROOT / "docs/V5_SECURITY_EVIDENCE.md").read_text(encoding="utf-8")
    require(results, "SAST workflow", "bandit" in workflow.lower(), "Bandit SAST is configured")
    require(results, "dependency audit", "pip-audit" in workflow.lower(), "pip-audit is configured")
    require(results, "filesystem scan", "scan-type: fs" in workflow, "Trivy filesystem scan is configured")
    require(results, "container scan", "image-ref:" in workflow, "Trivy image scan is configured")
    require(results, "fail on high severity", 'exit-code: "1"' in workflow, "security scans fail the workflow on findings")
    require(results, "review boundary", "security certification" in review.lower(), "review document states the verification boundary")
    failures = [item for item in results if not item[1]]
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
