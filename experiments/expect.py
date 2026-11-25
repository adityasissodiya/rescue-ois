"""Evaluate a scenario's stated expectations against the independent checker's result.

Expectation keys (all optional):
  violations          exact set of violation codes (positive runs use [])
  violations_include  codes that must be found (witnesses and negative controls)
  min                 {metric: minimum}            e.g. {"accepted": 3}
  equal               {"metric.key": value}         e.g. {"last_accept.e1:A": 139}
  no_accept_between   [[a, b], ...]   no acceptance at real time a <= t <= b
  accept_between      [[a, b], ...]   at least one acceptance at real time a <= t <= b
  refusals            ["signer:reason", ...] each refused at least once
  rejections          ["reason", ...]          each verifier rejection reason occurs
"""

from __future__ import annotations


def _get(metrics: dict, path: str):
    cur = metrics
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def evaluate(expect: dict, result: dict) -> list[str]:
    fails: list[str] = []
    codes = set(result["codes"])
    m = result["metrics"]
    if "violations" in expect and codes != set(expect["violations"]):
        fails.append(
            f"violations {sorted(codes)} != expected {sorted(expect['violations'])}"
        )
    missing = set(expect.get("violations_include", [])) - codes
    if missing:
        fails.append(f"expected violations not found: {sorted(missing)}")
    for key, low in expect.get("min", {}).items():
        val = _get(m, key)
        if val is None or val < low:
            fails.append(f"{key} = {val}, expected >= {low}")
    for key, want in expect.get("equal", {}).items():
        val = _get(m, key)
        if val != want:
            fails.append(f"{key} = {val}, expected {want}")
    times = [a[0] for a in m["accepts"]]
    for a, b in expect.get("no_accept_between", []):
        hit = [t for t in times if a <= t <= b]
        if hit:
            fails.append(f"acceptances in [{a}, {b}] at {hit}")
    for a, b in expect.get("accept_between", []):
        if not any(a <= t <= b for t in times):
            fails.append(f"no acceptance in [{a}, {b}]")
    for item in expect.get("refusals", []):
        if not m["refusals"].get(item):
            fails.append(f"refusal {item} did not occur")
    for reason in expect.get("rejections", []):
        if not m["rejected_by_reason"].get(reason):
            fails.append(f"rejection {reason} did not occur")
    return fails
