# XAITA-OT V5 — Day 37 Product Support Lock

**Status:** COMPLETE / LOCKED

## Scope

Day 37 closes the V5 P2 **Product support** requirement with an executable maintenance/support policy and coordinated vulnerability-disclosure process.

## Delivered

- Versioned support policy: `XAITA-OT-SUPPORT-1.0`.
- Supported scope: current `main` and latest tagged release.
- Monthly maintenance review cadence.
- Security review trigger for reported vulnerabilities and production/customer deployment.
- Severity taxonomy: Critical, High, Medium, Low.
- Explicit acknowledgement and triage targets.
- Private handling requirement for sensitive vulnerabilities.
- Coordinated disclosure policy.
- Safe reporting requirements that exclude credentials, secrets, customer-sensitive telemetry and personal data.
- Upgrade policy tied to Day 34 backup/verification/rollback controls.
- Machine-readable `xaita support-check` CLI validation.
- Regression coverage for policy validity, severity classification and fail-closed disclosure rules.
- `SECURITY.md` vulnerability-reporting guidance.
- `SUPPORT.md` maintenance and support boundaries.

## Acceptance criteria

1. Maintenance policy is versioned and machine-readable. — **PASS**
2. Supported release scope is explicit. — **PASS**
3. Severity and response targets are explicit. — **PASS**
4. Sensitive vulnerability reporting is kept out of public issues. — **PASS**
5. Coordinated disclosure is explicitly enabled. — **PASS**
6. Support policy has executable validation and regression tests. — **PASS**
7. Upgrade support is linked to verified backup/rollback procedures. — **PASS**
8. Final repository CI is green on the Day 37 lock commit. — **PENDING FINAL CI**

## Verification boundary

The support policy provides project-level maintenance and vulnerability-reporting expectations. It is not a contractual SLA, uptime commitment, legal guarantee, security certification, penetration-test attestation, regulatory approval, or customer production-support agreement. Customer-specific commitments require a separate written agreement.

## OT safety boundary

Support and vulnerability handling do not authorize control-plane writes or autonomous OT action.
