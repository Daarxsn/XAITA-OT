# XAITA-OT V5 — Day 36 Governance Lock

**Status:** COMPLETE / LOCKED

## Scope

Day 36 closes the V5 P2 **Governance** requirement with machine-readable dataset/legal/license controls and explicit customer deployment boundaries.

## Governance policy

The canonical policy is `configs/governance.yaml.json` and is versioned as `XAITA-OT-GOVERNANCE-1.0`.

### Dataset controls

- **SWaT:** `review_required`; current iTrust terms must be verified before redistribution or commercial use.
- **BATADAL:** `review_required`; organizer authorization/credentials and supplied usage terms must be retained with the experiment record.
- **TON-IoT:** `review_required`; applicable UNSW terms must be retained and permission obtained before commercial/company deployment or redistribution.

The policy intentionally does **not** convert these source-level requirements into an approval claim.

### Project/deployment controls

Commercial use, production use and redistribution remain `review_required` under the repository's research/controlled-evaluation license boundary.

Customer production deployment requires evidence for:

- dataset terms recorded
- dependency license review complete
- project license review complete
- security review complete
- customer OT segmentation review complete
- approved data ownership and permissions
- approved retention and audit policy

Autonomous OT control is explicitly **prohibited** by the governance policy.

## Executable governance gate

Validate the policy:

```powershell
xaita governance-check
```

Provide deployment evidence only after the corresponding reviews are actually complete:

```powershell
xaita governance-check --evidence-json <approved-evidence.json> --out artifacts/governance/decision.json
```

The command returns `review_required` and exit code 2 until every required evidence item is explicitly true.

## Acceptance criteria

1. Governance policy is versioned and machine-readable. — **PASS**
2. SWaT/BATADAL/TON-IoT controls preserve source-specific license/access requirements. — **PASS**
3. Project commercial/production/redistribution boundary is explicit. — **PASS**
4. Customer deployment evidence requirements are explicit. — **PASS**
5. Governance validation fails closed. — **PASS**
6. Autonomous OT control remains prohibited. — **PASS**
7. CLI and regression tests cover governance decisions. — **PASS**
8. Final repository CI is green on the Day 36 lock commit. — **PASS**

## Verification boundary

This governance contract records required review evidence; it is not a legal opinion, license grant, copyright clearance, customer authorization, regulatory approval, security certification, or OT safety certification. Legal/licensing decisions must be made by the appropriate rights holder, counsel, dataset provider, customer and security authority.

## OT safety boundary

The governance gate cannot authorize control-plane writes or autonomous OT action.
