# ADR-0005: Device Revocation Under Partition

## Status

Proposed

## Context

The security model integrates with the organizational CA. Device certificates can be revoked centrally. However, revocation propagation requires WAN connectivity from the core to each vehicle. A partitioned vehicle K430 cannot learn that a tablet certificate was revoked five minutes ago at HQ.

This is a fundamental trade-off, not an oversight. We need to decide what the system does in the gap.

## Decision

Revocation under partition will follow a **fail-safe-after-grace** model:

- Vehicle K430s pull a Certificate Revocation List (CRL) or perform OCSP-stapling refresh on every successful WAN reconnect; the CRL is cached locally with its `nextUpdate` field.
- Tablet client certificates are validated by `ops-api` against the locally cached CRL.
- If the local CRL is older than its `nextUpdate` plus a configurable grace window (default 24 hours), `ops-api` continues to accept tablet writes but emits a `CRL_STALE` warning audit event on every request, so operators can see the degraded state on the command vehicle's status panel.
- Beyond a hard cutoff (default 72 hours), `ops-api` switches to a fail-closed posture for new tablet sessions. Existing sessions remain usable to avoid breaking an active incident, but new tablet enrolment is refused until WAN returns.
- Lost-tablet drills must include the partitioned-vehicle case.

## Consequences

**Positive:**

- The behaviour under partition is now explicit, not implicit. Operators can see "CRL stale" on their status panel and know what it means.
- The grace window is short enough to limit exposure but long enough to not break realistic Norrbotten incident durations.

**Negative:**

- A short grace window means a partitioned vehicle becomes harder to use over time; this is intentional.
- Configuration drift between vehicles (different CRL ages) is normal and must be tolerated by ops.

## Open Questions

- Should the grace window be reduced when the vehicle is in command role? (Higher impact of accepting from a revoked tablet on incident state.)
- Is there a manual override for known-good operators? (Risk of abuse.)
