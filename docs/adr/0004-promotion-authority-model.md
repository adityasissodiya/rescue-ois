# ADR-0004: Promotion Authority Model

## Status

Proposed

This ADR describes the target authority model. The running services do not yet
store durable per-incident command epochs or reject stale command traffic after
promotion.

## Context

ADR-0001 establishes that exactly one K430 per incident writes to `incident.journal`. The recovery procedure (Flow 6) promotes a designated responder by running `scripts/promote-responder.sh` on it, flipping `EDGE_ROLE` from `responder` to `command`. The script itself is currently authorized by whichever credential allows shell access to the K430 (operator login or SSH key). This is "manual" only in the sense that a human invokes it; it is not "authorized" in any cryptographic sense beyond the host-level credential.

For an incident-management context, the question of *who is allowed to make a vehicle the command vehicle* is operationally meaningful and audit-relevant. The current model conflates host access with promotion authority.

## Decision

Promotion remains manual and operator-driven. In addition, every production
promotion should require a per-incident **promotion token** or equivalent
authorization artifact that must be presented alongside the host-level
invocation:

- The regional core issues a short-lived, signed promotion token bound to `(incident_id, vehicle_id, operator_subject)` when the incident is dispatched, plus on demand when a promotion is requested.
- The token is delivered to the vehicle K430 over the WireGuard overlay if WAN is present, or pre-issued at dispatch time as part of the bootstrap bundle.
- `scripts/promote-responder.sh` requires a valid, unexpired token at invocation; without one, the script refuses to flip `EDGE_ROLE`.
- The token is verified against the existing organizational CA chain. No new identity stack is introduced.
- Every promotion event (success and refusal) is written to the audit log with the token identifier and the operator subject extracted from the operator's certificate.

## Consequences

**Positive:**

- Promotion authority is bound to organizational identity, not just host access.
- Every promotion is auditable end-to-end: token issuance at core, presentation at vehicle, success or failure on the K430.
- Lost-laptop or stolen-K430 scenarios cannot promote without a current token.

**Negative:**

- Pre-issuing promotion tokens at dispatch time is the only way to support promotion under WAN partition. Token lifetime must be long enough to cover realistic incident durations but short enough to limit abuse if a vehicle is captured.
- Adds an integration dependency on the core's signing infrastructure.
- The current `promote-responder.sh` must be updated to enforce this; tests must cover the rejection path and stale-epoch rejection.

## Open Questions

- What is the default token lifetime? (Proposal: 24 hours, configurable per region.)
- Should multi-operator approval be required for promotion under WAN partition? (Out of scope for v1.)
