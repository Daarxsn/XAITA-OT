# XAITA-OT V5 — Day 4 Lock

## Status

**DAY 4 — LOCKED**

Day 4 establishes the controlled-deployment security and operational hardening baseline without changing the research model or benchmark semantics.

## Completed

- API authentication supports API-key and Bearer-token access.
- Explicit RBAC levels: viewer, analyst, admin.
- Production/staging environments require authentication by default.
- Legacy `xaita-api-key` compatibility retained.
- Dataset, benchmark and system-status reads are viewer-accessible.
- Event analysis and local experiment execution require analyst-level access.
- Request IDs are generated/propagated for traceability.
- Structured HTTP audit logs include request ID, route, status and duration.
- Security response headers are applied globally.
- Optional trusted-host enforcement is configured.
- Optional HTTPS redirect and HSTS are configured.
- CORS is disabled unless explicitly configured with trusted origins.
- GZip response compression is enabled for larger responses.
- Request-size bounds remain enforced through `XAITA_MAX_EVENTS`.
- Local rate limiting protects expensive analysis/experiment endpoints.
- `/v2/system` exposes deployment, dataset and security posture to authorized users.
- `/health` and `/ready` remain backward-compatible.
- Docker runtime uses a non-root user, read-only filesystem, dropped Linux capabilities, `no-new-privileges`, and a constrained `/tmp` filesystem.
- Deployment security configuration is documented in `docs/V5_DEPLOYMENT_HARDENING.md` and `.env.example`.
- API security and compatibility tests were expanded.

## Deliberately not claimed by this lock

- TLS certificate management inside the application.
- Enterprise SSO/LDAP/OIDC integration.
- Distributed rate limiting.
- OT network integration or live PLC/RTU/SCADA control.
- FAT/SAT, OT safety certification, penetration testing, or organizational security accreditation.
- Production benchmark performance claims beyond reproducible authorized runs.

Those are separate acceptance activities and must not be represented as completed merely because the Day 4 hardening baseline is complete.

## Release rule

Do not modify Day 4 security behavior casually. Any security change after this document must add/adjust tests and update this lock document with a new commit.
