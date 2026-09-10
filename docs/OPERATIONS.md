# Operations Guide

## Passive deployment principle

Run XAITA-OT on mirrored telemetry, SIEM/OT monitoring exports, historian/process data, or other approved read-only feeds. Do not connect the module to control-plane write paths for autonomous response.

## Production checklist

- [ ] Dataset and telemetry ownership/permissions approved
- [ ] Network segmentation and firewall policy reviewed
- [ ] Secrets stored outside source code
- [ ] API authentication/RBAC enabled by deployment platform
- [ ] TLS terminated at approved gateway
- [ ] Audit logging enabled and retained per policy
- [ ] Model/version provenance recorded
- [ ] ATT&CK mapping release pinned and reviewed
- [ ] Thresholds validated on environment-specific validation data
- [ ] Load/latency tested at expected event rates
- [ ] Human validation workflow established
- [ ] Incident-response and rollback procedures tested
- [ ] Safety/security review completed before production use
