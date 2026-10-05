# Support and Maintenance

## Scope

XAITA-OT is maintained as a research/engineering prototype baseline. The current support policy is configs/support_policy.json.

Supported scope:

- current main
- latest tagged release

Support requests should include the affected commit/version, environment, reproducible steps, expected behavior, actual behavior, relevant logs with secrets removed, and whether the issue is security-sensitive.

## Maintenance

- Maintenance review: monthly.
- Security review: on reported vulnerabilities and before production/customer deployment.
- Security fixes may require upgrading to a supported release.
- Run the Day 34 backup/verification/rollback workflow before upgrades.

## Support boundaries

The repository does not promise:

- uptime or availability
- contractual response SLAs
- customer-specific support obligations
- production OT safety certification
- penetration-test certification
- regulatory compliance
- customer deployment authorization

Customer-specific support, SLAs and deployment commitments require a separate written agreement and environment-specific review.

## Vulnerabilities

Sensitive vulnerabilities must use the private security-reporting path rather than a public issue. See SECURITY.md.
