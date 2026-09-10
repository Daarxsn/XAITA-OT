# Release Readiness

## Current state

The repository is a **working research/engineering prototype baseline** with a complete analytical skeleton and local API/dashboard. It is not represented as a certified production OT security product.

## Required before commercial customer deployment

1. Validate against real SWaT/BATADAL/TON-IoT benchmark files with reproducible chronological/episode-aware splits.
2. Replace demo/configured ATT&CK mappings with a version-pinned, reviewed ATT&CK data package.
3. Add authentication, authorization, tenant isolation, encrypted transport, secret management, secure logging and update/signing process.
4. Add full baseline/ablation/sensitivity/cross-environment experiments and archive immutable experiment manifests.
5. Load-test the ingestion and analysis path at target event rates.
6. Conduct SAST/dependency/container scanning and independent penetration/security review.
7. Validate deployment architecture against the customer's OT segmentation and safety policy.
8. Establish incident response, model rollback, audit retention, backup and disaster recovery procedures.
9. Complete legal/licensing review for datasets, dependencies and commercial distribution.
10. Establish product support, upgrade and vulnerability-disclosure processes.
