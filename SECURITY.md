# Security Policy

## Reporting a vulnerability

Please do **not** publish sensitive vulnerability details in a public issue.

Use the repository's configured private security-reporting mechanism when available. Include:

- affected version or commit
- affected component
- impact summary
- reproduction steps or minimal proof
- known mitigations

Do not include credentials, production secrets, customer-sensitive telemetry, personal data, or unnecessary weaponized exploit material.

XAITA-OT follows coordinated disclosure for reported vulnerabilities. Acknowledgement and triage targets are policy targets, not contractual SLAs.

## Severity targets

| Severity | Acknowledgement target | Triage target |
|---|---|---|
| Critical | 1 business day | 2 business days |
| High | 2 business days | 5 business days |
| Medium | 3 business days | 10 business days |
| Low | 5 business days | Next maintenance review |

These targets do not guarantee remediation time, availability, or customer-specific response commitments.

## Security boundaries

XAITA-OT is an analyst-support security analytics system. It does not issue PLC/RTU/SCADA control commands or authorize autonomous OT action.

Production/customer deployment requires the governance, security and environment-specific reviews documented in docs/RELEASE_READINESS.md and configs/governance.yaml.json.
