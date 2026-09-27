# XAITA-OT V5 Deployment Hardening

## Purpose

This runbook defines the minimum controlled-deployment posture for the XAITA-OT V5 analyst-support platform. It complements the research/validation workflow; it does not constitute OT safety certification, FAT/SAT, or a security accreditation.

## 1. Authentication and roles

Use API authentication for staging and production. Set `XAITA_ENV=staging` or `XAITA_ENV=production`; authentication is then required even if `XAITA_REQUIRE_AUTH` is not set.

Preferred role model:

- `viewer`: read-only system, dataset and benchmark status.
- `analyst`: viewer access plus `/v1/analyze` and `/v2/experiment`.
- `admin`: analyst access plus administrative deployment ownership outside this API surface.

For a small deployment, `XAITA_API_KEY` may be used with `XAITA_API_KEY_ROLE`. For multi-user deployments, configure `XAITA_API_KEYS_JSON` through a secrets manager rather than committing it to source control.

The API accepts `X-XAITA-API-Key` or `Authorization: Bearer <token>`. The older `xaita-api-key` header remains supported for compatibility.

## 2. Network controls

Set `XAITA_ALLOWED_HOSTS` to the exact DNS names/IPs used by the deployment. Keep `XAITA_CORS_ORIGINS` empty unless a browser client is served from a different trusted origin. If TLS is terminated by XAITA-OT itself, enable `XAITA_FORCE_HTTPS=true`; otherwise enforce HTTPS at the reverse proxy/load balancer.

Do not expose the development Uvicorn port directly to an untrusted OT network. Place the service behind the organization's approved network segmentation, firewall and reverse-proxy controls.

## 3. Resource protection

`XAITA_MAX_EVENTS` bounds request size. `XAITA_RATE_LIMIT_PER_MINUTE` protects expensive local analysis and experiment endpoints with a process-local limit. Multi-replica deployments must additionally enforce rate limits at the ingress/API gateway.

Large benchmark experiments should run in an isolated worker/job system rather than blocking a user-facing API process. The current endpoint is intentionally a controlled local execution path.

## 4. Auditability

Each request receives an `X-Request-ID` response header. Requests are emitted as structured JSON log records containing request ID, method, path, status, duration and client address. Application logs should be forwarded to the organization's approved centralized logging/SIEM system with retention and access controls appropriate to the environment.

Do not log API keys, Authorization headers, raw benchmark records, or sensitive OT payloads.

## 5. Dataset handling

Real SWaT, BATADAL and TON-IoT files remain deployment-local and must not be committed to Git. Configure mounted paths with `XAITA_SWAT_PATH`, `XAITA_BATADAL_PATH`, and `XAITA_TONIOT_PATH` where the conventional `data/raw/...` paths are unsuitable.

Use `/v2/datasets` and `/v2/system` to verify that all expected datasets are mounted and contain CSV files before an authorized validation run.

## 6. Container posture

The supplied container runs as the non-root `xaita` user and includes a health check. Keep the container filesystem read-only where the deployment permits it. Mount benchmark data read-only when possible. Persist logs through the deployment platform rather than writing them into the application image.

## 7. Release gate

Before a company handoff, require:

1. CI green on supported Python versions.
2. Dependency audit clean or explicitly reviewed exceptions.
3. API authentication tested with viewer/analyst/admin credentials.
4. Dataset readiness verified for each authorized benchmark.
5. `/health`, `/ready`, `/v2/system`, `/v2/datasets` and the dashboard smoke-tested.
6. Real-data benchmark results tied to a reproducible dataset/configuration/seed record.
7. OT network integration reviewed and approved by the responsible OT/security team.
8. Backup, recovery, log retention and incident-response procedures documented.
9. Human validation retained for all security/attribution conclusions.

## 8. Safety boundary

XAITA-OT remains an analyst-support security analytics platform. It must not be used as an autonomous PLC/RTU/SCADA control path. Production acceptance requires the organization's own OT safety, cybersecurity and operational approval process.
