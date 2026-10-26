"""Devices, links and partition cases of the forest-fire scenario.

The topology follows the model document's setting figure. One link is added: a mesh link
between V1 and V3, so that in case P-C the commander's part of the mesh still contains a
second vehicle (S, sector South) and a handover inside the partition is possible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

CASES = ("none", "P-A", "P-B", "P-C")

SERVER = "SRV"

# Which device each person signs on. C and the operator work at the regional centre,
# wired to the server; we fold their workstations into the server node.
PERSON_DEVICE = {"A": "HA", "B": "V2", "S": "V3", "C": SERVER, "OP": SERVER}

# Crew devices are readers: they receive orders and never sign decisions.
CREW_DEVICE = {"K1": "K12", "K2": "K12", "K3": "K34", "K4": "K34", "K5": "K5"}
CREWS = tuple(CREW_DEVICE)

DEVICES = (SERVER, "HA", "V1", "V2", "V3", "K12", "K34", "K5")
READERS = ("K12", "K34", "K5")

# One-way latency per link type, in seconds. Gossip adds up to one sync period per hop.
LATENCY = {"cellular": 0.15, "mesh": 0.05, "wifi": 0.01, "wired": 0.005}


@dataclass(frozen=True, slots=True)
class Interval:
    start: float
    end: float  # math.inf for "never comes back"

    def contains(self, t: float) -> bool:
        return self.start <= t < self.end


@dataclass(slots=True)
class Link:
    a: str
    b: str
    kind: str
    latency: float
    down_ab: list[Interval] = field(default_factory=list)  # a cannot send to b
    down_ba: list[Interval] = field(default_factory=list)  # b cannot send to a

    def up(self, src: str, t: float) -> bool:
        down = self.down_ab if src == self.a else self.down_ba
        return not any(iv.contains(t) for iv in down)

    def cut(self, iv: Interval, *, direction: str | None = None) -> None:
        """Take the link down; ``direction`` is the sending end, or None for both."""
        if direction in (None, self.a):
            self.down_ab.append(iv)
        if direction in (None, self.b):
            self.down_ba.append(iv)

    def other(self, end: str) -> str:
        return self.b if end == self.a else self.a


def forest_fire_links(latency: dict[str, float] | None = None) -> list[Link]:
    lat = LATENCY | (latency or {})
    spec = [
        ("HA", SERVER, "cellular"),
        ("V1", SERVER, "cellular"),
        ("V2", SERVER, "cellular"),
        ("V3", SERVER, "cellular"),
        ("HA", "V1", "wifi"),
        ("V1", "V2", "mesh"),
        ("V2", "V3", "mesh"),
        ("V1", "V3", "mesh"),
        ("V2", "K12", "mesh"),
        ("V3", "K34", "mesh"),
        ("V1", "K5", "mesh"),
    ]
    return [Link(a, b, kind, lat[kind]) for a, b, kind in spec]


def apply_case(links: list[Link], case: str, start: float, duration: float, *,
               oneway: str | None = None) -> None:
    """Cut the links that define a partition case, for ``[start, start + duration)``.

    P-A: only A's device is cut off. P-B: every vehicle loses its cellular link; the mesh
    still works. P-C: P-B, and the mesh splits so that A and B are in different parts.
    ``oneway`` (P-A only): "mute", A's device receives but nothing it sends arrives; or
    "deaf", what A's device sends arrives but it receives nothing.
    """
    if case not in CASES:
        raise ValueError(f"unknown case {case!r}; expected one of {CASES}")
    if oneway is not None and (case != "P-A" or oneway not in ("mute", "deaf")):
        raise ValueError("oneway is 'mute' or 'deaf', and defined for P-A only")
    iv = Interval(start, start + duration if math.isfinite(duration) else math.inf)
    a_device = PERSON_DEVICE["A"]
    for link in links:
        if case == "P-A" and a_device in (link.a, link.b):
            if oneway == "mute":
                link.cut(iv, direction=a_device)
            elif oneway == "deaf":
                link.cut(iv, direction=link.other(a_device))
            else:
                link.cut(iv)
        elif case in ("P-B", "P-C") and link.kind == "cellular":
            link.cut(iv)
        if case == "P-C" and {link.a, link.b} in ({"V1", "V2"}, {"V2", "V3"}):
            link.cut(iv)


def random_flaps(links: list[Link], rng, horizon: float, *, mean_up: float,
                 mean_down: float, start: float = 0.0) -> None:
    """Independent on/off flapping on every link, both directions together."""
    for link in links:
        t = start + rng.expovariate(1.0 / mean_up)
        while t < horizon:
            d = rng.expovariate(1.0 / mean_down)
            link.cut(Interval(t, min(t + d, horizon)))
            t += d + rng.expovariate(1.0 / mean_up)
