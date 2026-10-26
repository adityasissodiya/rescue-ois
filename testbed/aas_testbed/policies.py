"""Succession policies S0-S5 of the paper's Table II, as configuration.

A policy is two things: what the holder's device enforces on its own (a lease or a
timeout), and who may move command, on which trigger. Where the paper leaves a mechanism
open, the choice made here is stated in ``description`` and in ``MODEL CHOICE`` comments
in ``sim.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

POLICIES = ("S0", "S1", "S2", "S3", "S3L", "S4", "S5")


@dataclass(frozen=True, slots=True)
class Policy:
    name: str
    description: str
    # Enforcement on the holder's device.
    lease: float | None = None  # stop after L without hearing from the server
    primary_timeout: float | None = None  # T': the primary stops after T' without the deputy
    # Who moves command, and on which trigger.
    deputy_timeout: float | None = None  # T: the deputy activates after the primary is silent
    promotion: str | None = None  # "immediate" (S1) or "after_lease" (S2), by the operator
    superior_takeover: bool = False  # C takes over after failing to reach A by voice
    margin: float = 10.0  # S2: wait L + margin after the server last heard A

    def label(self) -> str:
        parts = [self.name]
        if self.lease is not None:
            parts.append(f"L={self.lease:g}")
        if self.deputy_timeout is not None:
            parts.append(f"T={self.deputy_timeout:g}")
        if self.primary_timeout is not None:
            parts.append(f"T'={self.primary_timeout:g}")
        return " ".join(parts)


def make_policy(
    name: str,
    *,
    lease: float = 90.0,
    timeout: float = 300.0,
    primary_timeout: float | None = None,
    margin: float = 10.0,
) -> Policy:
    """A policy with the paper's parameter names: ``lease`` is L, ``timeout`` is T, and
    ``primary_timeout`` is T' (default T - 60 s)."""
    t_prime = timeout - 60.0 if primary_timeout is None else primary_timeout
    match name:
        case "S0":
            return Policy(
                "S0",
                "No succession during a partition: no act moves command, A never stops.",
            )
        case "S1":
            return Policy(
                "S1",
                "Immediate promotion through the core: the operator promotes B once A is "
                "silent at the core and B reaches it; every holder stops after L without "
                "the core. This is the prototype's policy.",
                lease=lease,
                promotion="immediate",
            )
        case "S2":
            return Policy(
                "S2",
                "Promotion after the old lease expires: as S1, but the core promotes B only "
                "once it has not heard A for L + margin, or while A's device is reachable.",
                lease=lease,
                promotion="after_lease",
                margin=margin,
            )
        case "S3":
            return Policy(
                "S3",
                "Takeover by C: when the core no longer hears A, or someone reports A "
                "unfit, C calls A on voice; if A does not answer, C takes over and "
                "appoints B. A's device has no timeout.",
                superior_takeover=True,
            )
        case "S3L":
            return Policy(
                "S3L",
                "S3 with a lease on A's side: every holder stops after L without the core.",
                superior_takeover=True,
                lease=lease,
            )
        case "S4":
            return Policy(
                "S4",
                "Pre-authorized deputy activation: B activates after A's device has been "
                "silent for T; A's device stops after T' without hearing B's.",
                deputy_timeout=timeout,
                primary_timeout=t_prime,
            )
        case "S5":
            return Policy(
                "S5",
                "Both record, reconcile later: B activates after T of silence; A never "
                "stops. The plural boundary case.",
                deputy_timeout=timeout,
            )
    raise ValueError(f"unknown policy {name!r}; expected one of {POLICIES}")


def with_params(policy: Policy, **changes) -> Policy:
    return replace(policy, **changes)
