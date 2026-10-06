"""V5.1 Day 39 release-closure gate.

This gate verifies repository-level release evidence without pretending that
CI, external deployment, benchmark execution, or customer acceptance occurred.
It is intentionally fail-closed: missing contract evidence is a review state.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_LOCK_DOCS = [
    "docs/V5_DAY4_LOCK.md",
    "docs/V5_DAY5_LOCK.md",
    "docs/V5_DAY6_LOCK.md",
    "docs/V5_DAY7_OPERATIONAL_LOCK.md",
    "docs/V5_DAY8_DEPLOYMENT_INTEGRATION_LOCK.md",
    "docs/V5_DAY9_EVIDENCE_PROVENANCE_LOCK.md",
    "docs/V5_DAY10_ATTRIBUTION_QUALITY_LOCK.md",
    "docs/V5_DAY11_OPERATIONAL_ROBUSTNESS_LOCK.md",
    "docs/V5_DAY12_RELEASE_READINESS_LOCK.md",
    "docs/V5_DAY13_RELEASE_HANDOVER_LOCK.md",
    "docs/V5_DAY14_RELEASE_CANDIDATE_LOCK.md",
    "docs/V5_DAY15_CLEAN_INSTALL_LOCK.md",
    "docs/V5_DAY16_DEPLOYMENT_SECURITY_LOCK.md",
    "docs/V5_DAY17_RELEASE_PROVENANCE_LOCK.md",
    "docs/V5_DAY18_RELEASE_GOVERNANCE_LOCK.md",
    "docs/V5_DAY19_BASELINE_HARDENING_LOCK.md",
    "docs/V5_DAY20_REAL_DATA_VALIDATION_LOCK.md",
    "docs/V5_DAY21_REAL_EXPERIMENT_LOCK.md",
    "docs/V5_DAY22_FOUR_DETECTOR_EXPERIMENT_LOCK.md",
    "docs/V5_DAY23_CROSS_DATASET_EXPERIMENT_MATRIX_LOCK.md",
    "docs/V5_DAY24_MULTI_SEED_STATISTICAL_EVALUATION_LOCK.md",
    "docs/V5_DAY25_RESEARCH_ARTIFACT_PACKAGING_LOCK.md",
    "docs/V5_DAY26_ATTRIBUTION_EVALUATION_LOCK.md",
    "docs/V5_DAY27_EXPLANATION_FIDELITY_LOCK.md",
    "docs/V5_DAY28_EXECUTION_LIFECYCLE_LOCK.md",
    "docs/V5_DAY29_EXPERIMENT_MANIFEST_LOCK.md",
    "docs/V5_DAY30_DATA_DRIVEN_DASHBOARD_LOCK.md",
    "docs/V5_DAY31_ATTTCK_CTI_PACKAGE_LOCK.md",
    "docs/V5_DAY32_SECURITY_EVIDENCE_LOCK.md",
    "docs/V5_DAY33_ENTERPRISE_INTEGRATION_LOCK.md",
    "docs/V5_DAY34_RECOVERY_LIFECYCLE_LOCK.md",
    "docs/V5_DAY35_OPERATIONS_DOCUMENTATION_LOCK.md",
    "docs/V5_DAY36_GOVERNANCE_LOCK.md",
    "docs/V5_DAY37_PRODUCT_SUPPORT_LOCK.md",
]

REQUIRED_CONTRACTS = [
    "docs/V5.1_DEVELOPER_CONTRACT.md",
    "docs/V5.1_RELEASE_GATE.md",
    "docs/V5.1_BASELINE_HARDENING_ISSUES.md",
    "docs/V5_RELEASE_CANDIDATE.md",
    "docs/V5_ROADMAP.md",
    "README.md",
]

REQUIRED_TESTS = [
    "tests/test_v5_contract.py",
    "tests/test_v5_preflight.py",
    "tests/test_v5_operational_check.py",
    "tests/test_v5_real_data_runner.py",
    "tests/test_v510_release_provenance.py",
    "tests/test_v533_enterprise_integrations.py",
    "tests/test_v534_lifecycle_operations.py",
    "tests/test_v535_user_acceptance.py",
    "tests/test_v536_governance.py",
    "tests/test_v537_support_policy.py",
    "tests/test_v54_operational_hardening.py",
    "tests/test_v55_release_readiness.py",
    "tests/test_v56_release_manifest.py",
    "tests/test_v58_clean_install.py",
    "tests/test_v59_security_posture.py",
]

REQUIRED_WORKFLOWS = [
    ".github/workflows/ci.yml",
    ".github/workflows/v5-preflight.yml",
    ".github/workflows/v5-operational-check.yml",
    ".github/workflows/v5-clean-install.yml",
    ".github/workflows/v5-security-posture.yml",
    ".github/workflows/v5-release-candidate.yml",
    ".github/workflows/v5-release-provenance.yml",
    ".github/workflows/v5-security-evidence.yml",
]


def _missing(root: Path, paths: list[str]) -> list[str]:
    return [path for path in paths if not (root / path).is_file()]


def evaluate(root: Path) -> dict:
    root = root.resolve()
    checks = {
        "historical_lock_documents": not _missing(root, REQUIRED_LOCK_DOCS),
        "release_contracts": not _missing(root, REQUIRED_CONTRACTS),
        "regression_tests": not _missing(root, REQUIRED_TESTS),
        "release_workflows": not _missing(root, REQUIRED_WORKFLOWS),
        "raw_benchmark_data_policy": (
            (root / "README.md").is_file()
            and "Raw benchmark files are never written by the command." in (root / "README.md").read_text()
            and "Do not place proprietary or restricted benchmark files in source control." in (root / "README.md").read_text()
        ),
        "research_integrity_boundary": (
            (root / "README.md").is_file()
            and "No benchmark result should be presented as achieved" in (root / "README.md").read_text()
            and "analyst-support security analytics system" in (root / "README.md").read_text()
        ),
    }

    missing = {
        "historical_lock_documents": _missing(root, REQUIRED_LOCK_DOCS),
        "release_contracts": _missing(root, REQUIRED_CONTRACTS),
        "regression_tests": _missing(root, REQUIRED_TESTS),
        "release_workflows": _missing(root, REQUIRED_WORKFLOWS),
    }
    passed = all(checks.values())

    return {
        "gate": "XAITA-OT-V5.1-DAY39-RELEASE-CLOSURE",
        "status": "pass" if passed else "review_required",
        "checks": checks,
        "missing": missing,
        "external_evidence": {
            "ci": "verified by CI workflow on the final candidate commit",
            "benchmark_execution": "requires researcher-supplied authorized real datasets",
            "live_deployment": "requires deployment-specific verification",
            "customer_acceptance": "requires customer-specific evidence",
        },
        "claim_boundary": (
            "Repository closure does not claim benchmark superiority, "
            "production deployment, security certification, OT safety certification, "
            "or customer acceptance."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the V5.1 Day 39 release-closure gate.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = evaluate(args.root)
    payload = json.dumps(result, indent=2, sort_keys=True)
    print(payload)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
